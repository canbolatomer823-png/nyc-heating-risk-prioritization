import { useEffect, useMemo, useState } from 'react';
import {
  createMatch,
  createReservation,
  fetchFields,
  fetchHighlights,
  fetchMatches,
  submitJoinRequest,
} from './data/mockApi';
import './App.css';

const slotStatusClass = {
  available: 'slot available',
  pending: 'slot pending',
  booked: 'slot booked',
};

const slotStatusLabel = {
  available: 'Müsait',
  pending: 'Onay Bekliyor',
  booked: 'Rezerve',
};

function App() {
  const [fields, setFields] = useState([]);
  const [matches, setMatches] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [bookingForm, setBookingForm] = useState({
    teamName: '',
    players: 10,
    slotId: '',
  });
  const [matchForm, setMatchForm] = useState({
    fieldId: '',
    title: '',
    date: '',
    time: '',
    missingPlayers: 2,
    totalPlayers: 10,
    skillLevel: 'Orta',
    feePerPlayer: 150,
    organizerName: '',
    organizerNote: '',
  });
  const [joinNotes, setJoinNotes] = useState({});
  const [toast, setToast] = useState({ message: '', tone: 'success' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedField = useMemo(
    () => fields.find((field) => field.id === selectedFieldId),
    [fields, selectedFieldId],
  );

  useEffect(() => {
    const loadData = async () => {
      try {
        const [fieldResponse, matchResponse, highlightResponse] =
          await Promise.all([fetchFields(), fetchMatches(), fetchHighlights()]);
        setFields(fieldResponse);
        setMatches(matchResponse);
        setHighlights(highlightResponse);
        setSelectedFieldId(fieldResponse?.[0]?.id ?? null);
      } catch (error) {
        setToast({ message: error.message, tone: 'error' });
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedField) return;
    const firstSlot =
      selectedField.slots.find((slot) => slot.status !== 'booked')?.id || '';
    setBookingForm((prev) => ({
      ...prev,
      slotId: firstSlot,
    }));
    setMatchForm((prev) => ({
      ...prev,
      fieldId: selectedField.id,
    }));
  }, [selectedField]);

  useEffect(() => {
    if (!toast.message) return;
    const timeout = setTimeout(() => setToast({ message: '', tone: 'success' }), 3200);
    return () => clearTimeout(timeout);
  }, [toast]);

  const handleBookSlot = async (event) => {
    event.preventDefault();
    if (!selectedField || !bookingForm.slotId) {
      setToast({ message: 'Lütfen bir slot seçin', tone: 'error' });
      return;
    }
    try {
      setIsSubmitting(true);
      const updatedField = await createReservation({
        fieldId: selectedField.id,
        slotId: bookingForm.slotId,
        teamName: bookingForm.teamName || 'İsimsiz Takım',
        players: bookingForm.players,
      });
      setFields((prev) =>
        prev.map((field) => (field.id === updatedField.id ? updatedField : field)),
      );
      setToast({ message: 'Rezervasyon isteği iletildi', tone: 'success' });
      setBookingForm((prev) => ({ ...prev, teamName: '' }));
    } catch (error) {
      setToast({ message: error.message, tone: 'error' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateMatch = async (event) => {
    event.preventDefault();
    if (!matchForm.fieldId || !matchForm.date || !matchForm.time) {
      setToast({ message: 'Lütfen maç tarihi ve saatini girin', tone: 'error' });
      return;
    }
    try {
      setIsSubmitting(true);
      const newMatch = await createMatch(matchForm);
      setMatches((prev) => [newMatch, ...prev]);
      setToast({ message: 'Eksik oyuncu ilanı yayınlandı', tone: 'success' });
      setMatchForm((prev) => ({
        ...prev,
        title: '',
        date: '',
        time: '',
        missingPlayers: 2,
        totalPlayers: 10,
        organizerNote: '',
      }));
    } catch (error) {
      setToast({ message: error.message, tone: 'error' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJoinRequest = async (matchId) => {
    const note = joinNotes[matchId] || '';
    try {
      setIsSubmitting(true);
      const updatedMatch = await submitJoinRequest({
        matchId,
        playerName: 'Misafir Oyuncu',
        note,
      });
      setMatches((prev) =>
        prev.map((match) => (match.id === updatedMatch.id ? updatedMatch : match)),
      );
      setToast({ message: 'Katılım isteğin gönderildi', tone: 'success' });
      setJoinNotes((prev) => ({ ...prev, [matchId]: '' }));
    } catch (error) {
      setToast({ message: error.message, tone: 'error' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Urban FC Ankara MVP</p>
        <h1>Halısaha rezervasyonu ve eksik oyuncu yönetimi</h1>
        <p className="hero-copy">
          Ankara’daki sahalar için gerçek zamanlı slot takibi, IBAN doğrulaması ve topluluk
          özellikleri tek uygulamada. Aşağıdaki dummy verilerle uçtan uca senaryoları
          deneyimleyin.
        </p>
      </header>

      {toast.message && <div className={`toast ${toast.tone}`}>{toast.message}</div>}

      <main>
        <section>
          <div className="section-header">
            <div>
              <h2>Sahalar</h2>
              <p>Ankara genelindeki işletmelerin IBAN ve konum detayları</p>
            </div>
            <span className="pill">Dummy veri</span>
          </div>
          <div className="field-grid">
            {fields.map((field) => (
              <article
                key={field.id}
                className={`field-card ${
                  field.id === selectedFieldId ? 'active' : ''
                }`}
                onClick={() => setSelectedFieldId(field.id)}
              >
                <header>
                  <h3>{field.name}</h3>
                  <p>
                    {field.district} · {field.city}
                  </p>
                </header>
                <dl>
                  <div>
                    <dt>Adres</dt>
                    <dd>{field.address}</dd>
                  </div>
                  <div>
                    <dt>IBAN</dt>
                    <dd>{field.iban}</dd>
                  </div>
                  <div>
                    <dt>Yetkili</dt>
                    <dd>
                      {field.contactName} · {field.contactPhone}
                    </dd>
                  </div>
                  <div>
                    <dt>Saatlik Ücret</dt>
                    <dd>{field.pricePerHour.toLocaleString('tr-TR')} TL</dd>
                  </div>
                </dl>
                <div className="feature-row">
                  {field.features.map((feature) => (
                    <span key={feature} className="chip">
                      {feature}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>

        {selectedField && (
          <section className="field-detail">
            <div className="section-header">
              <div>
                <h2>{selectedField.name}</h2>
                <p>
                  {selectedField.address} · {selectedField.surface}
                </p>
              </div>
              <div className="iban-card">
                <p>IBAN</p>
                <strong>{selectedField.iban}</strong>
                <span>{selectedField.bankName}</span>
              </div>
            </div>
            <div className="detail-grid">
              <div className="card">
                <h3>Slot Takvimi</h3>
                <ul className="slot-list">
                  {selectedField.slots.map((slot) => (
                    <li key={slot.id} className={slotStatusClass[slot.status]}>
                      <div>
                        <strong>
                          {slot.date} · {slot.startTime}-{slot.endTime}
                        </strong>
                        <span>{slotStatusLabel[slot.status]}</span>
                      </div>
                      {slot.pendingFor && <small>{slot.pendingFor} opsiyonladı</small>}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="card">
                <h3>Rezervasyon Talebi</h3>
                <form onSubmit={handleBookSlot} className="form-grid">
                  <label>
                    Takım Adı
                    <input
                      type="text"
                      value={bookingForm.teamName}
                      onChange={(event) =>
                        setBookingForm((prev) => ({
                          ...prev,
                          teamName: event.target.value,
                        }))
                      }
                      placeholder="Örn. Ankara Gece Kartalları"
                    />
                  </label>
                  <label>
                    Oyuncu Sayısı
                    <input
                      type="number"
                      value={bookingForm.players}
                      min={6}
                      max={14}
                      onChange={(event) =>
                        setBookingForm((prev) => ({
                          ...prev,
                          players: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Slot Seç
                    <select
                      value={bookingForm.slotId}
                      onChange={(event) =>
                        setBookingForm((prev) => ({
                          ...prev,
                          slotId: event.target.value,
                        }))
                      }
                    >
                      <option value="">Slot seçin</option>
                      {selectedField.slots.map((slot) => (
                        <option key={slot.id} value={slot.id}>
                          {slot.date} · {slot.startTime}-{slot.endTime} ({slotStatusLabel[slot.status]})
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="submit" disabled={isSubmitting}>
                    Rezervasyon talebi gönder
                  </button>
                </form>
              </div>
            </div>
          </section>
        )}

        <section className="create-section">
          <div className="card">
            <h3>Eksik oyuncu ilanı oluştur</h3>
            <form onSubmit={handleCreateMatch} className="form-grid">
              <label>
                Saha
                <select
                  value={matchForm.fieldId}
                  onChange={(event) =>
                    setMatchForm((prev) => ({ ...prev, fieldId: event.target.value }))
                  }
                >
                  <option value="">Saha seçin</option>
                  {fields.map((field) => (
                    <option key={field.id} value={field.id}>
                      {field.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Başlık
                <input
                  type="text"
                  value={matchForm.title}
                  onChange={(event) =>
                    setMatchForm((prev) => ({ ...prev, title: event.target.value }))
                  }
                  placeholder="Örn. Salı Gece Ligi"
                />
              </label>
              <label>
                Tarih
                <input
                  type="date"
                  value={matchForm.date}
                  onChange={(event) =>
                    setMatchForm((prev) => ({ ...prev, date: event.target.value }))
                  }
                />
              </label>
              <label>
                Saat
                <input
                  type="time"
                  value={matchForm.time}
                  onChange={(event) =>
                    setMatchForm((prev) => ({ ...prev, time: event.target.value }))
                  }
                />
              </label>
              <label>
                Toplam Oyuncu
                <input
                  type="number"
                  value={matchForm.totalPlayers}
                  min={8}
                  max={14}
                  onChange={(event) =>
                    setMatchForm((prev) => ({
                      ...prev,
                      totalPlayers: Number(event.target.value),
                    }))
                  }
                />
              </label>
              <label>
                Eksik Sayısı
                <input
                  type="number"
                  value={matchForm.missingPlayers}
                  min={1}
                  max={6}
                  onChange={(event) =>
                    setMatchForm((prev) => ({
                      ...prev,
                      missingPlayers: Number(event.target.value),
                    }))
                  }
                />
              </label>
              <label>
                Beceri Seviyesi
                <select
                  value={matchForm.skillLevel}
                  onChange={(event) =>
                    setMatchForm((prev) => ({ ...prev, skillLevel: event.target.value }))
                  }
                >
                  <option>Hobi</option>
                  <option>Orta</option>
                  <option>Orta+</option>
                  <option>Rekabetçi</option>
                </select>
              </label>
              <label>
                Kişi Başı Ücret (TL)
                <input
                  type="number"
                  value={matchForm.feePerPlayer}
                  min={100}
                  step={10}
                  onChange={(event) =>
                    setMatchForm((prev) => ({
                      ...prev,
                      feePerPlayer: Number(event.target.value),
                    }))
                  }
                />
              </label>
              <label>
                Organizatör Adı
                <input
                  type="text"
                  value={matchForm.organizerName}
                  onChange={(event) =>
                    setMatchForm((prev) => ({
                      ...prev,
                      organizerName: event.target.value,
                    }))
                  }
                  placeholder="Örn. Can Başaran"
                />
              </label>
              <label>
                Not
                <textarea
                  rows={3}
                  value={matchForm.organizerNote}
                  onChange={(event) =>
                    setMatchForm((prev) => ({
                      ...prev,
                      organizerNote: event.target.value,
                    }))
                  }
                  placeholder="Pozisyon tercihleri, takım tarzı vb."
                />
              </label>
              <button type="submit" disabled={isSubmitting}>
                İlan yayınla
              </button>
            </form>
          </div>
        </section>

        <section>
          <div className="section-header">
            <div>
              <h2>Eksik oyuncu ilanları</h2>
              <p>
                Ankara genelinden yayınlanan maç kartları; dummy veriyi
                güncellemek için formu kullanın.
              </p>
            </div>
          </div>
          <div className="match-grid">
            {matches.map((match) => {
              const fieldName =
                fields.find((field) => field.id === match.fieldId)?.name || 'Bilinmeyen saha';
              return (
                <article key={match.id} className="card match-card">
                  <header>
                    <h3>{match.title || fieldName}</h3>
                    <p>
                      {match.date} · {match.time} · {fieldName}
                    </p>
                  </header>
                  <dl>
                    <div>
                      <dt>Beceri</dt>
                      <dd>{match.skillLevel}</dd>
                    </div>
                    <div>
                      <dt>Eksik Sayısı</dt>
                      <dd>{match.missingPlayers}</dd>
                    </div>
                    <div>
                      <dt>Kişi Başı</dt>
                      <dd>{match.feePerPlayer} TL</dd>
                    </div>
                    <div>
                      <dt>Organizatör</dt>
                      <dd>{match.organizer.name}</dd>
                    </div>
                  </dl>
                  <p className="note">{match.organizer.note}</p>
                  <label className="join-label">
                    Katılım Notu
                    <textarea
                      rows={2}
                      value={joinNotes[match.id] || ''}
                      onChange={(event) =>
                        setJoinNotes((prev) => ({
                          ...prev,
                          [match.id]: event.target.value,
                        }))
                      }
                      placeholder="Pozisyonunuz, deneyiminiz, mesajınız..."
                    />
                  </label>
                  <button onClick={() => handleJoinRequest(match.id)} disabled={isSubmitting}>
                    Katılma isteği gönder
                  </button>
                </article>
              );
            })}
          </div>
        </section>

        <section>
          <div className="section-header">
            <div>
              <h2>Haftanın öne çıkanları</h2>
              <p>Topluluk etkileşimi için içerik akışı</p>
            </div>
          </div>
          <div className="highlight-grid">
            {highlights.map((item) => (
              <article key={item.id} className="card highlight-card">
                <p className="eyebrow">{item.type === 'goal' ? 'Gol' : 'Maç'}</p>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
