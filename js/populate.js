// js/populate.js
function formatDate(ticket) {
  if (!ticket.purchase_date || !ticket.purchase_date.$date) return "N/A";
  const d = new Date(ticket.purchase_date.$date);
  // Format local (ex. "2025-02-02 13:54:45")
  return d.toLocaleString("fr-CH");
}

window.addEventListener("DOMContentLoaded", () => {
  fetch("assets/petzi_webhook.events.json")
    .then((res) => res.json())
    .then((data) => {
      setupDashboard(data);
      setupTicketsPage(data);
      setupEventDashboard(data);
      setupEventAllTickets(data);
    })
    .catch((err) => console.error(err));
});

function setupDashboard(data) {
  const totalTicketsEl = document.getElementById("total-tickets");
  if (!totalTicketsEl) return; // pas sur dashboard.html

  // 1) Total billets
  totalTicketsEl.innerText = data.length;

  // 2) Revenu total
  let totalRevenue = 0;
  data.forEach((t) => {
    totalRevenue += parseFloat(t.details.ticket.price.amount);
  });
  const revenueEl = document.getElementById("total-revenue");
  revenueEl.innerText = totalRevenue.toFixed(2) + " CHF";

  // 3) Événement le plus vendu
  const countsByEvent = {};
  data.forEach((t) => {
    const ev = t.details.ticket.title;
    countsByEvent[ev] = (countsByEvent[ev] || 0) + 1;
  });
  let topEvent = "N/A";
  let maxCount = 0;
  for (let ev in countsByEvent) {
    if (countsByEvent[ev] > maxCount) {
      maxCount = countsByEvent[ev];
      topEvent = ev;
    }
  }
  document.getElementById("top-event").innerText = topEvent;

  // 4) Derniers achats (3)
  const sorted = [...data].sort(
    (a, b) => new Date(b.purchase_date.$date) - new Date(a.purchase_date.$date)
  );
  const recent = sorted.slice(0, 3);
  const recentList = document.getElementById("recent-tickets");

  recent.forEach((ticket) => {
    const li = document.createElement("li");
    li.classList.add("list-group-item");
    li.innerHTML = `
      Ticket ${ticket.details.ticket.number} - ${
      ticket.details.buyer.firstName
    } <br>
      <strong>Événement :</strong>
      <a href="event_dashboard.html?title=${encodeURIComponent(
        ticket.details.ticket.title
      )}">
        ${ticket.details.ticket.title}
      </a><br>
      <strong>Ville :</strong> ${
        ticket.details.ticket.sessions[0].location.city
      } <br>
      <strong>Date :</strong> ${formatDate(ticket)}
    `;
    recentList.appendChild(li);
  });

  // 5) Graphique répartition par événement
  const labels = Object.keys(countsByEvent);
  const values = Object.values(countsByEvent);
  const ctx = document.getElementById("eventChart").getContext("2d");
  new Chart(ctx, {
    type: "pie",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
          ],
        },
      ],
    },
    options: { responsive: true },
  });

  // 6) Liste d’événements
  const eventList = document.getElementById("event-list");
  labels.forEach((ev, i) => {
    const li = document.createElement("li");
    li.classList.add("list-group-item");
    li.innerHTML = `
      <a href="event_dashboard.html?title=${encodeURIComponent(ev)}">${ev}</a>
      - ${values[i]} billets vendus
    `;
    eventList.appendChild(li);
  });
}

function setupTicketsPage(data) {
  const tableBody = document.getElementById("tickets-table-body");
  if (!tableBody) return; // pas sur tickets.html

  const citySelect = document.getElementById("city");
  const categorySelect = document.getElementById("category");
  const filterForm = document.getElementById("filter-form");

  // 1) Récupère villes et catégories distinctes
  const cities = [
    ...new Set(data.map((t) => t.details.ticket.sessions[0].location.city)),
  ].sort();
  const categories = [
    ...new Set(data.map((t) => t.details.ticket.category)),
  ].sort();

  // 2) Remplit les <select>
  cities.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    citySelect.appendChild(opt);
  });
  categories.forEach((cat) => {
    const opt = document.createElement("option");
    opt.value = cat;
    opt.textContent = cat;
    categorySelect.appendChild(opt);
  });

  // 3) Lire la query (si tu veux conserver les filtres sur rechargement)
  const params = new URLSearchParams(window.location.search);
  citySelect.value = params.get("city") || "";
  categorySelect.value = params.get("category") || "";

  // 4) Affichage initial
  function render() {
    tableBody.innerHTML = "";
    // Filtrage
    let filtered = [...data];
    if (citySelect.value) {
      filtered = filtered.filter(
        (t) => t.details.ticket.sessions[0].location.city === citySelect.value
      );
    }
    if (categorySelect.value) {
      filtered = filtered.filter(
        (t) => t.details.ticket.category === categorySelect.value
      );
    }
    // Tri date descendante
    filtered.sort(
      (a, b) =>
        new Date(b.purchase_date.$date) - new Date(a.purchase_date.$date)
    );
    // Remplit le tableau
    filtered.forEach((t) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${t.details.ticket.number}</td>
        <td>
          <a href="event_dashboard.html?title=${encodeURIComponent(
            t.details.ticket.title
          )}">
            ${t.details.ticket.title}
          </a>
        </td>
        <td>${t.details.ticket.category}</td>
        <td>${t.details.ticket.price.amount} ${
        t.details.ticket.price.currency
      }</td>
        <td>${t.details.buyer.firstName} ${t.details.buyer.lastName}</td>
        <td>${t.details.buyer.email}</td>
        <td>${t.details.ticket.sessions[0].location.city}</td>
        <td>${formatDate(t)}</td>
      `;
      tableBody.appendChild(tr);
    });
  }
  render();

  // 5) Filtrer au submit
  filterForm.addEventListener("submit", (e) => {
    e.preventDefault();
    // Met à jour l’URL
    const newParams = new URLSearchParams();
    if (citySelect.value) newParams.set("city", citySelect.value);
    if (categorySelect.value) newParams.set("category", categorySelect.value);
    window.location.search = newParams.toString();
  });
}

function setupEventDashboard(data) {
  const titleEl = document.getElementById("event-title");
  if (!titleEl) return; // pas sur event_dashboard.html

  // 1) Récupère l’eventTitle
  const params = new URLSearchParams(window.location.search);
  const eventTitle = params.get("title");
  if (!eventTitle) return;

  // 2) Injecte
  document.getElementById("event-title").innerText = eventTitle;
  console.log("TEST");
  const linkAllTickets = document.getElementById("all-tickets-link");
  console.log(linkAllTickets);
  linkAllTickets.href =
    "event_all_tickets.html?title=" + encodeURIComponent(eventTitle);

  // 3) Filtre
  const evTickets = data.filter((t) => t.details.ticket.title === eventTitle);

  // 4) CA total
  let sum = 0;
  evTickets.forEach((t) => (sum += parseFloat(t.details.ticket.price.amount)));
  document.getElementById("event-revenue").innerText = sum.toFixed(2);

  // 5) Date/lieu
  if (evTickets.length > 0) {
    const d = new Date(evTickets[0].purchase_date.$date);
    document.getElementById("event-date").innerText =
      d.toLocaleDateString("fr-CH");
    document.getElementById("event-location").innerText =
      evTickets[0].details.ticket.sessions[0].location.name;
  }

  // 6) 5 derniers billets
  const sorted = [...evTickets].sort(
    (a, b) => new Date(b.purchase_date.$date) - new Date(a.purchase_date.$date)
  );
  const last5 = sorted.slice(0, 5);
  const table = document.getElementById("event-tickets");
  last5.forEach((t) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${t.details.ticket.number}</td>
      <td>${t.details.ticket.type}</td>
      <td>${t.details.ticket.category}</td>
      <td>${t.details.ticket.price.amount} ${
      t.details.ticket.price.currency
    }</td>
      <td>${t.details.buyer.firstName} ${t.details.buyer.lastName}</td>
      <td>${t.details.buyer.email}</td>
      <td>${t.details.ticket.sessions[0].location.city}</td>
      <td>${formatDate(t)}</td>
    `;
    table.appendChild(tr);
  });

  // 7) Graphiques
  // a) Ventes par jour
  const salesByDay = {};
  evTickets.forEach((t) => {
    const day = new Date(t.purchase_date.$date).toISOString().split("T")[0];
    salesByDay[day] = (salesByDay[day] || 0) + 1;
  });
  const sLabels = Object.keys(salesByDay);
  const sValues = Object.values(salesByDay);
  new Chart(document.getElementById("salesChart").getContext("2d"), {
    type: "line",
    data: {
      labels: sLabels,
      datasets: [
        {
          label: "Billets vendus",
          data: sValues,
          borderColor: "#36A2EB",
          fill: false,
        },
      ],
    },
    options: { responsive: true },
  });

  // b) Répartition par type
  const typeCount = {};
  evTickets.forEach((t) => {
    const typ = t.details.ticket.type;
    typeCount[typ] = (typeCount[typ] || 0) + 1;
  });
  new Chart(document.getElementById("ticketTypeChart").getContext("2d"), {
    type: "doughnut",
    data: {
      labels: Object.keys(typeCount),
      datasets: [
        {
          data: Object.values(typeCount),
          backgroundColor: [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
          ],
        },
      ],
    },
    options: { responsive: true },
  });

  // c) Répartition par ville
  const cityCount = {};
  evTickets.forEach((t) => {
    const city = t.details.ticket.sessions[0].location.city;
    cityCount[city] = (cityCount[city] || 0) + 1;
  });
  new Chart(document.getElementById("regionChart").getContext("2d"), {
    type: "bar",
    data: {
      labels: Object.keys(cityCount),
      datasets: [
        {
          data: Object.values(cityCount),
          backgroundColor: "#36A2EB",
        },
      ],
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: true } },
    },
  });
}

function setupEventAllTickets(data) {
  const tableBody = document.getElementById("event-all-tickets");
  if (!tableBody) return; // pas sur event_all_tickets.html

  // 1) Récupère param ?title
  const params = new URLSearchParams(window.location.search);
  const eventTitle = params.get("title");
  if (!eventTitle) return;

  document.getElementById("event-title-17").innerText =
    "Tous les billets pour " + eventTitle;

  // 2) Filtrer
  let evTickets = data.filter((t) => t.details.ticket.title === eventTitle);

  // 3) Récupère filtres
  const citySelect = document.getElementById("city");
  const typeSelect = document.getElementById("type");
  const sortSelect = document.getElementById("sort");
  const filterForm = document.getElementById("event-filter-form");

  // 4) Populate selects
  const distinctCities = [
    ...new Set(
      evTickets.map((t) => t.details.ticket.sessions[0].location.city)
    ),
  ].sort();
  const distinctTypes = [
    ...new Set(evTickets.map((t) => t.details.ticket.type)),
  ].sort();
  distinctCities.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    citySelect.appendChild(opt);
  });
  distinctTypes.forEach((tp) => {
    const opt = document.createElement("option");
    opt.value = tp;
    opt.textContent = tp;
    typeSelect.appendChild(opt);
  });

  // 5) Lire query
  citySelect.value = params.get("city") || "";
  typeSelect.value = params.get("type") || "";
  sortSelect.value = params.get("sort") || "date_desc";

  // 6) Fonction d’affichage
  function render() {
    let filtered = [...evTickets];
    if (citySelect.value) {
      filtered = filtered.filter(
        (t) => t.details.ticket.sessions[0].location.city === citySelect.value
      );
    }
    if (typeSelect.value) {
      filtered = filtered.filter(
        (t) => t.details.ticket.type === typeSelect.value
      );
    }
    // Tri
    if (sortSelect.value === "date_asc") {
      filtered.sort(
        (a, b) =>
          new Date(a.purchase_date.$date) - new Date(b.purchase_date.$date)
      );
    } else if (sortSelect.value === "date_desc") {
      filtered.sort(
        (a, b) =>
          new Date(b.purchase_date.$date) - new Date(a.purchase_date.$date)
      );
    } else if (sortSelect.value === "price_asc") {
      filtered.sort(
        (a, b) =>
          parseFloat(a.details.ticket.price.amount) -
          parseFloat(b.details.ticket.price.amount)
      );
    } else if (sortSelect.value === "price_desc") {
      filtered.sort(
        (a, b) =>
          parseFloat(b.details.ticket.price.amount) -
          parseFloat(a.details.ticket.price.amount)
      );
    }

    tableBody.innerHTML = "";
    filtered.forEach((t) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${t.details.ticket.number}</td>
        <td>${t.details.ticket.type}</td>
        <td>${t.details.ticket.category}</td>
        <td>${t.details.ticket.price.amount} ${
        t.details.ticket.price.currency
      }</td>
        <td>${t.details.buyer.firstName} ${t.details.buyer.lastName}</td>
        <td>${t.details.buyer.email}</td>
        <td>${t.details.ticket.sessions[0].location.city}</td>
        <td>${formatDate(t)}</td>
      `;
      tableBody.appendChild(tr);
    });
  }
  render();

  // 7) Au submit => rebuild URL
  filterForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const newParams = new URLSearchParams();
    newParams.set("title", eventTitle);
    if (citySelect.value) newParams.set("city", citySelect.value);
    if (typeSelect.value) newParams.set("type", typeSelect.value);
    if (sortSelect.value) newParams.set("sort", sortSelect.value);
    window.location.search = newParams.toString();
  });
}
