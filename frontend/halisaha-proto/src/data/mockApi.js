const wait = (value, delay = 500) =>
  new Promise((resolve) =>
    setTimeout(() => resolve(JSON.parse(JSON.stringify(value))), delay),
  );

const fields = [
  {
    id: 'field-ata',
    name: 'Ataç Spor Kompleksi',
    district: 'Çankaya',
    city: 'Ankara',
    address: 'İlker Mah. 1426. Sok. No:18, Çankaya/Ankara',
    iban: 'TR89 0006 2001 2345 6789 0001 23',
    bankName: 'Garanti BBVA Çankaya',
    contactName: 'Mert Yılmaz',
    contactPhone: '+90 555 111 22 33',
    pricePerHour: 1550,
    surface: 'Kapalı - Suni Çim',
    features: ['Otopark', 'Duş', 'Kafeterya', 'Canlı Yayın Kamerası'],
    coordinates: { lat: 39.8876, lng: 32.8441 },
    photos: ['/field-ata-1.jpg'],
    slots: [
      {
        id: 'slot-ata-1',
        date: '2024-09-24',
        startTime: '20:00',
        endTime: '21:00',
        status: 'available',
      },
      {
        id: 'slot-ata-2',
        date: '2024-09-24',
        startTime: '21:00',
        endTime: '22:00',
        status: 'pending',
        pendingFor: 'Ankara Tech FC',
      },
      {
        id: 'slot-ata-3',
        date: '2024-09-25',
        startTime: '19:00',
        endTime: '20:00',
        status: 'booked',
      },
    ],
  },
  {
    id: 'field-batikent',
    name: 'Batıkent Arena',
    district: 'Yenimahalle',
    city: 'Ankara',
    address: 'İvedik Cad. No:61, Yenimahalle/Ankara',
    iban: 'TR13 0011 1000 1234 5678 0000 52',
    bankName: 'Ziraat Bankası Batıkent',
    contactName: 'Elif Demir',
    contactPhone: '+90 553 654 09 21',
    pricePerHour: 1350,
    surface: 'Açık - Suni Çim',
    features: ['Soyunma Odası', 'Drone Çekimi', 'Otopark'],
    coordinates: { lat: 39.9684, lng: 32.7401 },
    photos: ['/field-batikent-1.jpg'],
    slots: [
      {
        id: 'slot-batikent-1',
        date: '2024-09-24',
        startTime: '20:30',
        endTime: '21:30',
        status: 'available',
      },
      {
        id: 'slot-batikent-2',
        date: '2024-09-25',
        startTime: '18:30',
        endTime: '19:30',
        status: 'available',
      },
    ],
  },
  {
    id: 'field-cayyolu',
    name: 'Çayyolu Prestige',
    district: 'Çayyolu',
    city: 'Ankara',
    address: 'Koru Mah. 2689. Cad. No:12, Çankaya/Ankara',
    iban: 'TR57 0006 7010 0000 0056 1234 78',
    bankName: 'Yapı Kredi Konutkent',
    contactName: 'Seda Kaya',
    contactPhone: '+90 541 987 34 56',
    pricePerHour: 1750,
    surface: 'Kapalı - Hibrit Çim',
    features: ['Tribün', 'Canlı Skorboard', 'Profesyonel Hakem'],
    coordinates: { lat: 39.8853, lng: 32.6906 },
    photos: ['/field-cayyolu-1.jpg'],
    slots: [
      {
        id: 'slot-cayyolu-1',
        date: '2024-09-23',
        startTime: '21:30',
        endTime: '22:30',
        status: 'available',
      },
      {
        id: 'slot-cayyolu-2',
        date: '2024-09-24',
        startTime: '22:30',
        endTime: '23:30',
        status: 'booked',
      },
    ],
  },
];

const matches = [
  {
    id: 'match-ank-001',
    fieldId: 'field-ata',
    title: 'Ankara Tech FC | Salı Gece Ligi',
    date: '2024-09-24',
    time: '21:00',
    skillLevel: 'Orta+',
    missingPlayers: 2,
    totalPlayers: 10,
    feePerPlayer: 160,
    organizer: { name: 'Can Başaran', note: 'Hızlı pas oyunu, hücumcu lazım.' },
    requests: [{ id: 'req-1', name: 'Barış', status: 'approved' }],
  },
  {
    id: 'match-ank-002',
    fieldId: 'field-batikent',
    title: 'Batıkent Akşam Grubu',
    date: '2024-09-25',
    time: '19:00',
    skillLevel: 'Hobi',
    missingPlayers: 3,
    totalPlayers: 12,
    feePerPlayer: 140,
    organizer: { name: 'Elçin', note: 'Kaleci ve defans öncelikli.' },
    requests: [],
  },
];

const highlights = [
  {
    id: 'highlight-1',
    type: 'goal',
    title: 'Haftanın Golü',
    description: 'Ozan Tok, 35 metreden aşırtma gol (Çayyolu Prestige)',
  },
  {
    id: 'highlight-2',
    type: 'match',
    title: 'Haftanın Maçı',
    description: 'Çayyolu Prestige derbisi 8-8 bitti, MVP: Berk Yılmaz',
  },
];

export const fetchFields = () => wait(fields);

export const fetchMatches = () => wait(matches);

export const fetchHighlights = () => wait(highlights);

export const createReservation = async ({ fieldId, slotId, teamName, players }) => {
  const field = fields.find((f) => f.id === fieldId);
  if (!field) {
    throw new Error('Saha bulunamadı');
  }
  const slot = field.slots.find((s) => s.id === slotId);
  if (!slot) {
    throw new Error('Slot bulunamadı');
  }
  if (slot.status === 'booked') {
    throw new Error('Slot zaten dolu');
  }
  slot.status = 'pending';
  slot.pendingFor = teamName;
  slot.players = players;
  return wait(field);
};

export const createMatch = async ({
  fieldId,
  title,
  date,
  time,
  missingPlayers,
  totalPlayers,
  skillLevel,
  feePerPlayer,
  organizerName,
  organizerNote,
}) => {
  const newMatch = {
    id: `match-${Date.now()}`,
    fieldId,
    title,
    date,
    time,
    missingPlayers,
    totalPlayers,
    skillLevel,
    feePerPlayer,
    organizer: { name: organizerName, note: organizerNote },
    requests: [],
  };
  matches.unshift(newMatch);
  return wait(newMatch);
};

export const submitJoinRequest = async ({ matchId, playerName, note }) => {
  const match = matches.find((m) => m.id === matchId);
  if (!match) {
    throw new Error('Maç bulunamadı');
  }
  const request = {
    id: `req-${Date.now()}`,
    name: playerName,
    note,
    status: 'pending',
  };
  match.requests.push(request);
  match.missingPlayers = Math.max(match.missingPlayers - 1, 0);
  return wait(match);
};
