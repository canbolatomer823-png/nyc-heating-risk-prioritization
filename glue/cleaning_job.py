"""Glue PySpark job to clean and enrich ingested data.

Convert the DynamicFrame from the Glue Catalog into a Spark DataFrame so we can
apply native Spark transformations. Write the cleaned data back to S3 in
Parquet format for efficient querying with Athena.
"""

import sys
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def run(job_name: str, database: str, table: str, output_path: str) -> None:
    spark_context = SparkContext()
    glue_context = GlueContext(spark_context)
    spark = glue_context.spark_session

    job = Job(glue_context)
    job.init(job_name, {})

    dynamic_frame = glue_context.create_dynamic_frame.from_catalog(
        database=database,
        table_name=table,
    )

    frame = dynamic_frame.toDF()

    frame = frame.dropDuplicates()
    frame = frame.withColumn("ingest_date", F.to_date("ingest_date"))

    frame = frame.withColumn(
        "record_hash",
        F.sha2(F.concat_ws("|", *[F.col(c).cast("string") for c in frame.columns]), 256),
    )

    processed = DynamicFrame.fromDF(frame, glue_context, "processed")

    glue_context.write_dynamic_frame.from_options(
        frame=processed,
        connection_type="s3",
        connection_options={"path": output_path},
        format="parquet",
    )

    job.commit()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("Usage: cleaning_job.py <JOB_NAME> <DATABASE> <TABLE> <OUTPUT_PATH>")
    _, job_name, database, table, output_path = sys.argv
    run(job_name, database, table, output_path)
