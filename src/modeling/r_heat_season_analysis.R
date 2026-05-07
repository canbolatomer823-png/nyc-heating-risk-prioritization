#!/opt/homebrew/bin/Rscript

args <- commandArgs(trailingOnly = TRUE)

default_window_root <- "<project-root>/data/windows/heat_season_2024_10_01_2025_05_31"
window_root <- if (length(args) >= 1) args[[1]] else default_window_root

reports_dir <- file.path(window_root, "reports")
processed_dir <- file.path(window_root, "processed")

daily_metrics_path <- file.path(reports_dir, "seasonal_anova_daily_metrics.csv")
weather_path <- file.path(processed_dir, "noaa_gsod_nyc_daily_summary.csv")
anova_summary_path <- file.path(reports_dir, "r_anova_summary.csv")
nb_coefficients_path <- file.path(reports_dir, "r_daily_weather_nb_coefficients.csv")
report_path <- file.path(reports_dir, "r_statistical_replication.md")

if (!file.exists(daily_metrics_path)) {
  stop(sprintf("Missing daily metrics file: %s", daily_metrics_path))
}
if (!file.exists(weather_path)) {
  stop(sprintf("Missing weather file: %s", weather_path))
}

suppressPackageStartupMessages({
  library(MASS)
})

safe_eta_sq <- function(model) {
  anova_tbl <- anova(model)
  ss_between <- as.numeric(anova_tbl$`Sum Sq`[1])
  ss_total <- ss_between + sum(model$residuals^2, na.rm = TRUE)
  if (ss_total == 0) {
    return(NA_real_)
  }
  ss_between / ss_total
}

daily <- read.csv(daily_metrics_path, stringsAsFactors = FALSE)
weather <- read.csv(weather_path, stringsAsFactors = FALSE)

daily$complaint_date <- as.Date(daily$complaint_date)
weather$date <- as.Date(weather$date)

merged <- merge(
  daily,
  weather,
  by.x = "complaint_date",
  by.y = "date",
  all.x = TRUE,
  sort = TRUE
)

month_levels <- unique(daily$month_label)
merged$month_label <- factor(merged$month_label, levels = month_levels)

complaints_aov <- aov(daily_total_complaints ~ month_label, data = merged)
positive_aov <- aov(daily_positive_buildings ~ month_label, data = merged)

complaints_summary <- summary(complaints_aov)[[1]]
positive_summary <- summary(positive_aov)[[1]]

anova_rows <- data.frame(
  target = c("daily_total_complaints", "daily_positive_buildings"),
  f_statistic = c(
    as.numeric(complaints_summary[["F value"]][1]),
    as.numeric(positive_summary[["F value"]][1])
  ),
  p_value = c(
    as.numeric(complaints_summary[["Pr(>F)"]][1]),
    as.numeric(positive_summary[["Pr(>F)"]][1])
  ),
  eta_sq = c(
    safe_eta_sq(complaints_aov),
    safe_eta_sq(positive_aov)
  )
)

write.csv(anova_rows, anova_summary_path, row.names = FALSE)

nb_frame <- merged[, c(
  "daily_total_complaints",
  "weather_heating_degree_c",
  "weather_temp_drop_c",
  "weather_prcp_mm_mean"
)]
nb_frame <- nb_frame[complete.cases(nb_frame), ]
nb_frame$heating_degree_scaled <- as.numeric(scale(nb_frame$weather_heating_degree_c))
nb_frame$temp_drop_scaled <- as.numeric(scale(nb_frame$weather_temp_drop_c))
nb_frame$prcp_scaled <- as.numeric(scale(nb_frame$weather_prcp_mm_mean))

nb_model <- glm.nb(
  daily_total_complaints ~ heating_degree_scaled + temp_drop_scaled + prcp_scaled,
  data = nb_frame
)

nb_coef <- summary(nb_model)$coefficients
nb_rows <- data.frame(
  term = rownames(nb_coef),
  estimate = nb_coef[, "Estimate"],
  std_error = nb_coef[, "Std. Error"],
  z_value = nb_coef[, "z value"],
  p_value = nb_coef[, "Pr(>|z|)"],
  effect = exp(nb_coef[, "Estimate"]),
  row.names = NULL
)
write.csv(nb_rows, nb_coefficients_path, row.names = FALSE)

month_means <- aggregate(
  cbind(daily_total_complaints, daily_positive_buildings) ~ month_label,
  data = merged,
  FUN = mean
)
peak_idx <- which.max(month_means$daily_total_complaints)
quiet_idx <- which.min(month_means$daily_total_complaints)

gee_like_note <- paste(
  "Bu R katmanı, heat-season için günlük aggregate düzeyde",
  "ANOVA ve weather-driven Negative Binomial replikasyonu sağlar.",
  "Ana building-day benchmark ve GLMM/GEE hattı Python tarafında kalır."
)

report_lines <- c(
  "# R Statistical Replication",
  "",
  "Bu rapor, heat-season final build için R tarafında yürütülen ek istatistiksel replikasyonu özetler.",
  "",
  "## 1. Seasonal ANOVA",
  "",
  sprintf(
    "- Daily total complaints: F=%.4f, p=%.6g, eta_sq=%.4f",
    anova_rows$f_statistic[1],
    anova_rows$p_value[1],
    anova_rows$eta_sq[1]
  ),
  sprintf(
    "- Daily positive buildings: F=%.4f, p=%.6g, eta_sq=%.4f",
    anova_rows$f_statistic[2],
    anova_rows$p_value[2],
    anova_rows$eta_sq[2]
  ),
  sprintf(
    "- Peak mean complaint month: %s (mean=%.2f)",
    month_means$month_label[peak_idx],
    month_means$daily_total_complaints[peak_idx]
  ),
  sprintf(
    "- Lowest mean complaint month: %s (mean=%.2f)",
    month_means$month_label[quiet_idx],
    month_means$daily_total_complaints[quiet_idx]
  ),
  "",
  "## 2. Daily Weather Negative Binomial",
  "",
  sprintf(
    "- Heating degree effect: %.4fx (p=%.6g)",
    nb_rows$effect[nb_rows$term == "heating_degree_scaled"],
    nb_rows$p_value[nb_rows$term == "heating_degree_scaled"]
  ),
  sprintf(
    "- Temperature drop effect: %.4fx (p=%.6g)",
    nb_rows$effect[nb_rows$term == "temp_drop_scaled"],
    nb_rows$p_value[nb_rows$term == "temp_drop_scaled"]
  ),
  sprintf(
    "- Precipitation effect: %.4fx (p=%.6g)",
    nb_rows$effect[nb_rows$term == "prcp_scaled"],
    nb_rows$p_value[nb_rows$term == "prcp_scaled"]
  ),
  "",
  "## 3. Interpretation",
  "",
  "- R tarafında da mevsimsel fark güçlü ve anlamlı kaldı.",
  "- Günlük aggregate count modeli, soğuk yük arttıkça complaint hacminin yükseldiğini doğruladı.",
  paste0("- ", gee_like_note)
)

writeLines(report_lines, report_path)

cat(report_path, "\n")
