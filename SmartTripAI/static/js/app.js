const state = {
  token: localStorage.getItem("smarttrip_token") || "",
  publicData: { destinations: [], buddies: [], feature_flags: {} },
  session: { user: null, trips: [], expenses: [], wishlist: [], notifications: [], reviews: [], chat: {}, packing: [], analytics: {} },
  currentPage: "home",
  currentPlan: null,
  currentBuddy: null,
  booking: { hotel: null, flight: null, activities: [] },
  maps: { itinerary: null, global: null },
  language: "en",
  theme: localStorage.getItem("smarttrip_theme") || "dark",
};

const MOODS = ["Peaceful", "Adventure", "Nature", "Party", "Romantic", "Spiritual", "Cultural", "Foodie", "Luxury"];
const DEALS = [
  { title: "Shoulder season advantage", body: "April to early June and September often produce the best price-to-weather ratio in Europe." },
  { title: "High-value mountain stays", body: "Swiss and Himalayan routes become dramatically more efficient when lodging is clustered near transit hubs." },
  { title: "Food-led city planning", body: "Keeping one major meal reservation daily reduces both budget drift and itinerary fatigue." },
];

const UI_TEXT = {
  en: {
    saved: "Saved successfully.",
    loginRequired: "Please login to use this feature.",
    planning: "Generating a realistic trip plan...",
    profileUpdated: "Profile updated.",
    settingsSaved: "Settings saved.",
    exported: "Export complete.",
  },
  hi: {
    saved: "सफलतापूर्वक सेव किया गया।",
    loginRequired: "यह फीचर इस्तेमाल करने के लिए लॉगिन करें।",
    planning: "वास्तविक ट्रिप प्लान तैयार किया जा रहा है...",
    profileUpdated: "प्रोफाइल अपडेट हो गई।",
    settingsSaved: "सेटिंग्स सेव हो गईं।",
    exported: "एक्सपोर्ट पूरा हुआ।",
  },
};

UI_TEXT.hi = {
  saved: "Safalta se save ho gaya.",
  loginRequired: "Is feature ke liye login karein.",
  planning: "Realistic trip plan taiyar ho raha hai...",
  profileUpdated: "Profile update ho gayi.",
  settingsSaved: "Settings save ho gayi.",
  exported: "Export complete ho gaya.",
};

const $ = (id) => document.getElementById(id);

function text(key) {
  return UI_TEXT[state.language]?.[key] || UI_TEXT.en[key] || key;
}

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const response = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    const message = payload.error || "Request failed";
    throw new Error(message);
  }
  return payload;
}

function setStatus(message) {
  $("globalStatus").textContent = message;
}

function toast(message, type = "success") {
  const node = document.createElement("div");
  node.className = `toast-item ${type}`;
  node.innerHTML = `<strong>${type === "error" ? "Issue" : "SmartTrip"}</strong><div class="small-muted mt-1">${escapeHtml(message)}</div>`;
  $("toastStack").appendChild(node);
  setTimeout(() => node.remove(), 3800);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function saveCache() {
  localStorage.setItem("smarttrip_cache", JSON.stringify({ publicData: state.publicData, session: state.session, currentPlan: state.currentPlan }));
}

function loadCache() {
  try {
    const raw = localStorage.getItem("smarttrip_cache");
    if (!raw) return false;
    const cached = JSON.parse(raw);
    state.publicData = cached.publicData || state.publicData;
    state.session = cached.session || state.session;
    state.currentPlan = cached.currentPlan || state.currentPlan;
    return true;
  } catch {
    return false;
  }
}

function setTheme(theme) {
  state.theme = theme;
  localStorage.setItem("smarttrip_theme", theme);
  document.documentElement.setAttribute("data-theme", theme);
  $("themeToggleBtn").textContent = theme === "dark" ? "Light mode" : "Dark mode";
}

function toggleTheme() {
  setTheme(state.theme === "dark" ? "light" : "dark");
  if ($("settingsDarkMode")) $("settingsDarkMode").checked = state.theme === "dark";
}

function updateNav() {
  const isAuthed = Boolean(state.session.user);
  $("navPublic").classList.toggle("d-none", isAuthed);
  $("navPrivate").classList.toggle("d-none", !isAuthed);
  if (isAuthed) {
    $("navAvatar").innerHTML = state.session.user.avatar?.startsWith("data:image")
      ? `<img src="${state.session.user.avatar}" alt="">`
      : escapeHtml(avatarLabel(state.session.user));
    $("navUserName").textContent = state.session.user.name.split(" ")[0];
  }
  $("adminNavItem").classList.toggle("d-none", state.session.user?.role !== "admin");
}

function avatarLabel(user) {
  if (!user) return "S";
  if (user.avatar?.startsWith("data:image")) return user.name?.slice(0, 1)?.toUpperCase() || "S";
  return user.avatar?.slice(0, 2).toUpperCase() || user.name?.slice(0, 1)?.toUpperCase() || "S";
}

function setPage(page) {
  state.currentPage = page;
  document.querySelectorAll(".page").forEach((section) => section.classList.remove("active"));
  const node = $(`page-${page}`);
  if (node) node.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (page === "dashboard") renderDashboard();
  if (page === "planner") renderPlannerSidePanels();
  if (page === "recommendation") renderRecommendation();
  if (page === "itinerary") renderItinerary();
  if (page === "booking") renderBooking();
  if (page === "expenses") renderExpenses();
  if (page === "map") renderGlobalMap();
  if (page === "trips") renderTrips();
  if (page === "wishlist") renderWishlist();
  if (page === "notifications") renderNotifications();
  if (page === "packing") renderPacking();
  if (page === "currency") renderCurrencyTools();
  if (page === "profile") renderProfile();
  if (page === "settings") renderSettings();
  if (page === "reviews") renderReviews();
  if (page === "buddies") renderBuddies();
  if (page === "admin") renderAdmin();
}

function requireAuth(page) {
  if (!state.session.user) {
    toast(text("loginRequired"), "error");
    setPage("login");
    return false;
  }
  setPage(page);
  return true;
}

async function bootstrap() {
  try {
    const response = await api("/api/bootstrap", { auth: Boolean(state.token) });
    state.publicData = response.data.destinations ? response.data : response.data || response;
    if (response.data.session) state.session = response.data.session;
    else if (response.session) state.session = response.session;
    saveCache();
  } catch (error) {
    const hasCache = loadCache();
    toast(hasCache ? "Loaded cached data because the server was unavailable." : error.message, hasCache ? "success" : "error");
  }
  state.language = state.session.user?.language || "en";
  updateNav();
  renderHome();
  if (state.session.user) renderDashboard();
  if (state.currentPlan) {
    renderRecommendation();
    renderItinerary();
    renderBooking();
  }
}

function renderHome() {
  $("featuredDestinations").innerHTML = state.publicData.destinations
    .map(
      (destination) => `
      <div class="col-md-6 col-xl-3">
        <button class="card-shell w-100 text-start h-100" data-destination="${escapeHtml(destination.name)}">
          <div class="eyebrow">${escapeHtml(destination.country)}</div>
          <h3>${escapeHtml(destination.name)}</h3>
          <p class="small-muted">${escapeHtml(destination.summary)}</p>
          <div class="suggestion-list mt-3">
            ${destination.tags.slice(0, 3).map((tag) => `<span class="suggestion-chip">${escapeHtml(tag)}</span>`).join("")}
          </div>
        </button>
      </div>`
    )
    .join("");

  document.querySelectorAll("[data-destination]").forEach((button) => {
    button.addEventListener("click", () => {
      $("planDestination").value = button.dataset.destination;
      $("homeDestination").value = button.dataset.destination;
      if (state.session.user) setPage("planner");
      else setPage("signup");
    });
  });

  $("featureGrid").innerHTML = [
    ["AI planner", "Exact-day itinerary generation from 1 to 30 days with realistic pacing and budget logic."],
    ["Weather intelligence", "Live weather snapshots and season-aware planning instead of static placeholders."],
    ["Maps and nearby places", "Live place search, route points, and interactive Leaflet maps."],
    ["Travel buddy matching", "Profiles, compatibility, chat, shared planning, and group coordination."],
    ["Budget and analytics", "SQLite-backed expense tracking, category totals, and exports."],
    ["Security and resilience", "Password hashing, sessions, client error logging, and offline cache support."],
  ]
    .map(
      ([title, body]) => `<div class="feature-card"><strong>${title}</strong><div class="small-muted">${body}</div></div>`
    )
    .join("");

  $("travelDeals").innerHTML = DEALS.map((deal) => `<div class="stack-item"><strong>${deal.title}</strong><div class="small-muted">${deal.body}</div></div>`).join("");
}

function renderDashboard() {
  const user = state.session.user;
  if (!user) return;
  $("dashboardGreeting").textContent = `Welcome back, ${user.name.split(" ")[0]}`;
  const analytics = state.session.analytics || { trip_count: 0, expense_total: 0, wishlist_count: 0, unread_notifications: 0 };
  $("dashboardStats").innerHTML = [
    ["Trips", analytics.trip_count || 0],
    ["Expenses", formatMoney(analytics.expense_total || 0, user.currency)],
    ["Wishlist", analytics.wishlist_count || 0],
    ["Unread alerts", analytics.unread_notifications || 0],
  ]
    .map(
      ([label, value]) => `<div class="col-md-3"><div class="metric-card"><span class="small-muted">${label}</span><strong>${value}</strong></div></div>`
    )
    .join("");

  if (state.currentPlan) {
    $("dashboardWeather").innerHTML = `
      <div class="stack-item">
        <strong>${escapeHtml(state.currentPlan.destination)}</strong>
        <div class="small-muted">${escapeHtml(state.currentPlan.weather.summary)} · ${state.currentPlan.weather.temperature_c}°C · Wind ${state.currentPlan.weather.windspeed_kmh} km/h</div>
      </div>`;
  } else {
    $("dashboardWeather").innerHTML = `<div class="empty-state compact-empty">Generate a plan to see live destination weather and operational context.</div>`;
  }

  const categoryTotals = state.session.analytics.category_totals || {};
  const maxValue = Math.max(1, ...Object.values(categoryTotals), 1);
  $("dashboardAnalytics").innerHTML = Object.keys(categoryTotals).length
    ? `<div class="chart-bars">${Object.entries(categoryTotals)
        .map(
          ([category, amount]) => `
          <div class="flex-fill">
            <div class="chart-bar" style="height:${Math.max(30, (amount / maxValue) * 160)}px"></div>
            <div class="chart-label">${escapeHtml(category)}<br>${formatMoney(amount, user.currency)}</div>
          </div>`
        )
        .join("")}</div>`
    : `<div class="empty-state compact-empty">Expenses will appear here once you begin tracking trip costs.</div>`;

  $("dashboardTrips").innerHTML = state.session.trips.length
    ? state.session.trips
        .slice(0, 3)
        .map(
          (trip) => `
          <div class="trip-card">
            <div class="d-flex justify-content-between gap-2 flex-wrap">
              <div>
                <strong>${escapeHtml(trip.destination)}</strong>
                <div class="small-muted">${trip.days} days · ${escapeHtml(trip.status)} · ${trip.start_date || "Flexible dates"}</div>
              </div>
              <button class="btn btn-app btn-ghost btn-sm" data-open-trip="${trip.id}" type="button">View</button>
            </div>
          </div>`
        )
        .join("")
    : `<div class="empty-state compact-empty">No trips yet. Build your first plan from the planner page.</div>`;

  document.querySelectorAll("[data-open-trip]").forEach((button) =>
    button.addEventListener("click", () => {
      const trip = state.session.trips.find((item) => item.id === Number(button.dataset.openTrip));
      if (trip) {
        state.currentPlan = trip.plan;
        saveCache();
        setPage("recommendation");
      }
    })
  );

  $("dashboardNotifications").innerHTML = state.session.notifications.length
    ? state.session.notifications.slice(0, 4).map(notificationCard).join("")
    : `<div class="empty-state compact-empty">No notifications yet.</div>`;

  $("dashboardBuddies").innerHTML = state.publicData.buddies.slice(0, 3).map((buddy) => buddyCard(buddy)).join("");
  attachBuddyButtons();
}

function renderPlannerSidePanels() {
  $("plannerChecks").innerHTML = [
    "Exact day count is enforced.",
    "Budget range is checked against destination cost profile.",
    "Nearby route points and local activity logic are included.",
    "Plan output stays aligned to companion type and traveler count.",
  ]
    .map((item) => `<div class="stack-item">${item}</div>`)
    .join("");

  const sampleResults = state.publicData.destinations
    .slice(0, 4)
    .map((destination) => `<div class="stack-item"><strong>${escapeHtml(destination.name)}</strong><div class="small-muted">${escapeHtml(destination.summary)}</div></div>`)
    .join("");
  $("liveSearchResults").innerHTML = sampleResults;
}

function renderRecommendation() {
  if (!state.currentPlan) {
    $("recommendationHero").innerHTML = `<div class="empty-state">No active recommendation yet. Use the planner to generate one.</div>`;
    return;
  }
  const plan = state.currentPlan;
  $("recommendationHero").innerHTML = `
    <div class="eyebrow">${escapeHtml(plan.country)} · ${plan.days} days</div>
    <h2>${escapeHtml(plan.destination)}</h2>
    <p class="small-muted">${escapeHtml(plan.description)}</p>
    <div class="result-grid">
      <div class="result-chip"><span class="small-muted">Estimated budget</span><strong>${escapeHtml(plan.budget_range)}</strong></div>
      <div class="result-chip"><span class="small-muted">Best season</span><strong>${escapeHtml(plan.best_season)}</strong></div>
      <div class="result-chip"><span class="small-muted">Companion mode</span><strong>${escapeHtml(plan.companion)}</strong></div>
      <div class="result-chip"><span class="small-muted">Quality check</span><strong>${plan.engine?.exact_day_count ? "Exact day match" : "Needs review"}</strong></div>
    </div>
  `;
  $("recommendationReasons").innerHTML = plan.recommendations.map((reason) => `<div class="stack-item">${escapeHtml(reason)}</div>`).join("");
  $("budgetBreakdown").innerHTML = plan.budget_breakdown
    .map(
      (bucket) => `
      <div class="stack-item">
        <div class="d-flex justify-content-between gap-2">
          <strong>${escapeHtml(bucket.category)}</strong>
          <span>${escapeHtml(bucket.amount)}</span>
        </div>
        <div class="progress-shell mt-2"><span style="width:${bucket.pct}%"></span></div>
      </div>`
    )
    .join("");
  $("travelTips").innerHTML = plan.travel_tips.map((tip) => `<div class="stack-item">${escapeHtml(tip)}</div>`).join("");
  $("recommendationWeather").innerHTML = `
    <div class="stack-item">
      <strong>${escapeHtml(plan.weather.summary)}</strong>
      <div class="small-muted">${plan.weather.temperature_c}°C · Wind ${plan.weather.windspeed_kmh} km/h · Source: ${escapeHtml(plan.weather.source)}</div>
    </div>`;
}

function renderItinerary() {
  const list = $("itineraryList");
  if (!state.currentPlan) {
    list.innerHTML = `<div class="empty-state">Generate a plan first.</div>`;
    return;
  }
  list.innerHTML = state.currentPlan.itinerary
    .map(
      (day) => `
      <div class="timeline-item card-shell">
        <div class="timeline-title">
          <div>
            <div class="eyebrow">Day ${day.day} · ${escapeHtml(day.date)}</div>
            <h3>${escapeHtml(day.title)}</h3>
          </div>
          <span class="status-pill">${escapeHtml(day.route_point.name)}</span>
        </div>
        <ul class="timeline-activities">
          ${day.activities.map((activity) => `<li>${escapeHtml(activity)}</li>`).join("")}
        </ul>
        <div class="timeline-meta">
          <div><strong>Stay</strong><div class="small-muted">${escapeHtml(day.accommodation)}</div></div>
          <div><strong>Food</strong><div class="small-muted">${escapeHtml(day.food_highlight)}</div></div>
          <div><strong>Transport</strong><div class="small-muted">${escapeHtml(day.transport_note)}</div></div>
        </div>
      </div>`
    )
    .join("");

  $("itineraryMapPlaces").innerHTML = state.currentPlan.nearby_places
    .map((place) => `<div class="stack-item"><strong>${escapeHtml(place.name)}</strong><div class="small-muted">${escapeHtml(place.kind || "Place")}</div></div>`)
    .join("");
  renderItineraryMap();
}

function buddyCard(buddy) {
  return `
    <div class="buddy-card">
      <div class="d-flex gap-3 align-items-start">
        <div class="buddy-avatar">${escapeHtml(buddy.avatar)}</div>
        <div class="flex-grow-1">
          <div class="d-flex justify-content-between gap-2">
            <strong>${escapeHtml(buddy.name)}</strong>
            <span class="status-pill">${buddy.match}% match</span>
          </div>
          <div class="small-muted">${escapeHtml(buddy.destination)} · ${escapeHtml(buddy.style)}</div>
          <p class="small-muted mt-2 mb-2">${escapeHtml(buddy.bio)}</p>
          <div class="suggestion-list">${buddy.interests.map((interest) => `<span class="suggestion-chip">${escapeHtml(interest)}</span>`).join("")}</div>
          <div class="d-flex gap-2 mt-3">
            <button class="btn btn-app btn-ghost btn-sm" type="button" data-buddy-detail="${buddy.id}">Profile</button>
            <button class="btn btn-app btn-primary btn-sm" type="button" data-buddy-chat="${buddy.id}">Connect</button>
          </div>
        </div>
      </div>
    </div>`;
}

function attachBuddyButtons() {
  document.querySelectorAll("[data-buddy-detail]").forEach((button) => {
    button.addEventListener("click", () => {
      const buddy = state.publicData.buddies.find((item) => item.id === Number(button.dataset.buddyDetail));
      if (!buddy) return;
      state.currentBuddy = buddy;
      renderBuddyDetail();
      setPage("buddy-detail");
    });
  });
  document.querySelectorAll("[data-buddy-chat]").forEach((button) => {
    button.addEventListener("click", () => {
      const buddy = state.publicData.buddies.find((item) => item.id === Number(button.dataset.buddyChat));
      if (!buddy) return;
      state.currentBuddy = buddy;
      renderChat();
      setPage("chat");
    });
  });
}

function renderBuddies() {
  const query = $("buddySearch")?.value?.trim().toLowerCase() || "";
  const style = $("buddyStyle")?.value || "";
  const filtered = state.publicData.buddies.filter((buddy) => {
    const matchesQuery = !query || buddy.name.toLowerCase().includes(query) || buddy.destination.toLowerCase().includes(query);
    const matchesStyle = !style || buddy.style === style;
    return matchesQuery && matchesStyle;
  });
  $("buddyGrid").innerHTML = filtered.length
    ? filtered.map((buddy) => `<div class="col-md-6">${buddyCard(buddy)}</div>`).join("")
    : `<div class="empty-state">No buddy matches found for that filter.</div>`;
  attachBuddyButtons();
}

function renderBuddyDetail() {
  const buddy = state.currentBuddy;
  if (!buddy) return;
  $("buddyDetailCard").innerHTML = `
    <div class="d-flex flex-column flex-lg-row gap-4">
      <div class="text-center">
        <div class="profile-avatar">${escapeHtml(buddy.avatar)}</div>
        <div class="status-pill mt-2">${buddy.match}% compatibility</div>
      </div>
      <div class="flex-grow-1">
        <div class="eyebrow">${escapeHtml(buddy.destination)}</div>
        <h2>${escapeHtml(buddy.name)}</h2>
        <p class="small-muted">${escapeHtml(buddy.bio)}</p>
        <div class="row g-3 mb-3">
          <div class="col-md-4"><div class="metric-card"><span class="small-muted">Age</span><strong>${buddy.age}</strong></div></div>
          <div class="col-md-4"><div class="metric-card"><span class="small-muted">Style</span><strong>${escapeHtml(buddy.style)}</strong></div></div>
          <div class="col-md-4"><div class="metric-card"><span class="small-muted">Rating</span><strong>${buddy.rating}</strong></div></div>
        </div>
        <div class="suggestion-list mb-3">${buddy.interests.map((interest) => `<span class="suggestion-chip">${escapeHtml(interest)}</span>`).join("")}</div>
        <button class="btn btn-app btn-primary" type="button" id="openBuddyChatBtn">Start chat</button>
      </div>
    </div>`;
  $("openBuddyChatBtn").addEventListener("click", () => {
    renderChat();
    setPage("chat");
  });
}

function renderChat() {
  const buddy = state.currentBuddy || state.publicData.buddies[0];
  state.currentBuddy = buddy;
  $("chatBuddyName").textContent = buddy.name;
  const messages = state.session.chat?.[String(buddy.id)] || [];
  $("chatMessages").innerHTML = messages
    .map((message) => `<div class="chat-bubble ${message.sender === "user" ? "user" : "buddy"}">${escapeHtml(message.message)}${message.attachment_type ? `<div class="small-muted mt-2">Attachment: ${escapeHtml(message.attachment_type)}</div>` : ""}</div>`)
    .join("");
  $("chatMessages").scrollTop = $("chatMessages").scrollHeight;
}

function renderBooking() {
  const plan = state.currentPlan;
  if (!plan) {
    $("hotelOptions").innerHTML = `<div class="empty-state compact-empty">Plan a trip before booking.</div>`;
    $("flightOptions").innerHTML = "";
    $("activityOptions").innerHTML = "";
    $("bookingSummary").innerHTML = "";
    return;
  }

  if (!state.booking.hotel && plan.hotels[0]) state.booking.hotel = plan.hotels[0];
  if (!state.booking.flight && plan.flights[0]) state.booking.flight = plan.flights[0];

  $("hotelOptions").innerHTML = plan.hotels
    .map(
      (hotel, index) => `
      <div class="option-card ${state.booking.hotel?.name === hotel.name ? "active" : ""}">
        <label class="d-flex justify-content-between gap-2">
          <div>
            <strong>${escapeHtml(hotel.name)}</strong>
            <div class="small-muted">${hotel.rating} · ${escapeHtml(hotel.location)}</div>
          </div>
          <div class="text-end">
            <div>${formatMoney(hotel.price, plan.budget_currency)}</div>
            <input type="radio" name="hotel" value="${index}" ${state.booking.hotel?.name === hotel.name ? "checked" : ""}>
          </div>
        </label>
      </div>`
    )
    .join("");

  $("flightOptions").innerHTML = plan.flights
    .map(
      (flight, index) => `
      <div class="option-card ${state.booking.flight?.name === flight.name ? "active" : ""}">
        <label class="d-flex justify-content-between gap-2">
          <div>
            <strong>${escapeHtml(flight.name)}</strong>
            <div class="small-muted">${escapeHtml(flight.type)} · ${escapeHtml(flight.duration)} · ${escapeHtml(flight.airline)}</div>
          </div>
          <div class="text-end">
            <div>${formatMoney(flight.price, plan.budget_currency)}</div>
            <input type="radio" name="flight" value="${index}" ${state.booking.flight?.name === flight.name ? "checked" : ""}>
          </div>
        </label>
      </div>`
    )
    .join("");

  $("activityOptions").innerHTML = plan.activities
    .map(
      (activity, index) => `
      <div class="option-card ${state.booking.activities.some((item) => item.name === activity.name) ? "active" : ""}">
        <label class="d-flex justify-content-between gap-2">
          <div>
            <strong>${escapeHtml(activity.name)}</strong>
            <div class="small-muted">${escapeHtml(activity.category)} · ${escapeHtml(activity.duration)} · ${escapeHtml(activity.description)}</div>
          </div>
          <div class="text-end">
            <div>${formatMoney(activity.price, plan.budget_currency)}</div>
            <input type="checkbox" name="activity" value="${index}" ${state.booking.activities.some((item) => item.name === activity.name) ? "checked" : ""}>
          </div>
        </label>
      </div>`
    )
    .join("");

  document.querySelectorAll('input[name="hotel"]').forEach((input) =>
    input.addEventListener("change", () => {
      state.booking.hotel = plan.hotels[Number(input.value)];
      renderBooking();
    })
  );
  document.querySelectorAll('input[name="flight"]').forEach((input) =>
    input.addEventListener("change", () => {
      state.booking.flight = plan.flights[Number(input.value)];
      renderBooking();
    })
  );
  document.querySelectorAll('input[name="activity"]').forEach((input) =>
    input.addEventListener("change", () => {
      const activity = plan.activities[Number(input.value)];
      if (input.checked) state.booking.activities.push(activity);
      else state.booking.activities = state.booking.activities.filter((item) => item.name !== activity.name);
      renderBooking();
    })
  );

  const total = bookingTotal();
  $("bookingSummary").innerHTML = `
    <div class="stack-list">
      <div class="stack-item d-flex justify-content-between"><span>Hotel</span><strong>${formatMoney(state.booking.hotel?.price || 0, plan.budget_currency)}</strong></div>
      <div class="stack-item d-flex justify-content-between"><span>Transport</span><strong>${formatMoney(state.booking.flight?.price || 0, plan.budget_currency)}</strong></div>
      <div class="stack-item d-flex justify-content-between"><span>Activities</span><strong>${formatMoney(state.booking.activities.reduce((sum, item) => sum + item.price, 0), plan.budget_currency)}</strong></div>
      <div class="stack-item d-flex justify-content-between"><span>Taxes and fees</span><strong>${formatMoney(45, plan.budget_currency)}</strong></div>
      <div class="stack-item d-flex justify-content-between"><span>Total</span><strong>${formatMoney(total, plan.budget_currency)}</strong></div>
    </div>`;
  $("paymentTotal").textContent = formatMoney(total, plan.budget_currency);
}

function bookingTotal() {
  const plan = state.currentPlan;
  if (!plan) return 0;
  return (state.booking.hotel?.price || 0) + (state.booking.flight?.price || 0) + state.booking.activities.reduce((sum, item) => sum + item.price, 0) + 45;
}

function renderExpenses() {
  const user = state.session.user;
  if (!user) return;
  const expenses = state.session.expenses || [];
  const total = expenses.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const budget = state.currentPlan?.budget_total || 5000;
  const pct = Math.min(100, Math.round((total / Math.max(budget, 1)) * 100));
  const categoryTotals = {};
  expenses.forEach((expense) => {
    categoryTotals[expense.category] = (categoryTotals[expense.category] || 0) + expense.amount;
  });
  $("expenseOverview").innerHTML = `
    <div class="row g-3">
      <div class="col-md-4"><div class="metric-card"><span class="small-muted">Budget</span><strong>${formatMoney(budget, user.currency)}</strong></div></div>
      <div class="col-md-4"><div class="metric-card"><span class="small-muted">Spent</span><strong>${formatMoney(total, user.currency)}</strong></div></div>
      <div class="col-md-4"><div class="metric-card"><span class="small-muted">Remaining</span><strong>${formatMoney(Math.max(0, budget - total), user.currency)}</strong></div></div>
    </div>
    <div class="progress-shell mt-3"><span style="width:${pct}%"></span></div>
    <div class="small-muted mt-2">${pct}% of active trip budget used</div>
    <div class="chart-bars">${Object.entries(categoryTotals)
      .map(
        ([category, amount]) => `
        <div class="flex-fill">
          <div class="chart-bar" style="height:${Math.max(25, (amount / Math.max(...Object.values(categoryTotals), 1)) * 140)}px"></div>
          <div class="chart-label">${escapeHtml(category)}<br>${formatMoney(amount, user.currency)}</div>
        </div>`
      )
      .join("")}</div>`;

  $("expenseList").innerHTML = expenses.length
    ? expenses
        .map(
          (expense) => `
          <div class="expense-row">
            <div class="d-flex justify-content-between gap-3 flex-wrap">
              <div>
                <strong>${escapeHtml(expense.description)}</strong>
                <div class="small-muted">${escapeHtml(expense.category)} · ${escapeHtml(expense.expense_date)} · ${escapeHtml(expense.trip_label || "No trip label")}</div>
              </div>
              <div class="d-flex align-items-center gap-2">
                <strong>${formatMoney(expense.amount, user.currency)}</strong>
                <button class="btn btn-app btn-ghost btn-sm" type="button" data-delete-expense="${expense.id}">Delete</button>
              </div>
            </div>
          </div>`
        )
        .join("")
    : `<div class="empty-state">No expenses recorded yet.</div>`;

  document.querySelectorAll("[data-delete-expense]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        const response = await api(`/api/expenses/${button.dataset.deleteExpense}`, { method: "DELETE" });
        replaceSession(response.data);
        renderExpenses();
        renderDashboard();
      } catch (error) {
        toast(error.message, "error");
      }
    })
  );
}

function renderGlobalMap() {
  if (!state.maps.global) {
    state.maps.global = L.map("globalMap").setView([20, 10], 2);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(state.maps.global);
  }
  const map = state.maps.global;
  clearDynamicLayers(map);
  const points = state.currentPlan?.nearby_places || state.publicData.destinations.map((destination) => ({ name: destination.name, lat: destination.coords.lat, lng: destination.coords.lng, kind: destination.country }));
  if (points.length) {
    const bounds = [];
    points.forEach((place) => {
      const marker = L.marker([place.lat, place.lng]).addTo(map);
      marker.bindPopup(`<strong>${escapeHtml(place.name)}</strong><br>${escapeHtml(place.kind || "Place")}`);
      bounds.push([place.lat, place.lng]);
    });
    if (bounds.length > 1) map.fitBounds(bounds, { padding: [30, 30] });
    else map.setView(bounds[0], 11);
  }
  $("mapPlaces").innerHTML = points.map((place) => `<div class="stack-item"><strong>${escapeHtml(place.name)}</strong><div class="small-muted">${escapeHtml(place.kind || "Place")}</div></div>`).join("");
  setTimeout(() => map.invalidateSize(), 50);
}

function renderItineraryMap() {
  if (!state.currentPlan) return;
  if (!state.maps.itinerary) {
    state.maps.itinerary = L.map("itineraryMap").setView([state.currentPlan.coordinates.lat, state.currentPlan.coordinates.lng], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(state.maps.itinerary);
  }
  const map = state.maps.itinerary;
  clearDynamicLayers(map);
  const points = state.currentPlan.route_points || [];
  const latlngs = points.map((point) => [point.lat, point.lng]);
  points.forEach((point) => {
    const marker = L.marker([point.lat, point.lng]).addTo(map);
    marker.bindPopup(`<strong>${escapeHtml(point.name)}</strong>`);
  });
  if (latlngs.length) {
    L.polyline(latlngs, { color: "#38c0ff", weight: 4 }).addTo(map);
    map.fitBounds(latlngs, { padding: [25, 25] });
  } else {
    map.setView([state.currentPlan.coordinates.lat, state.currentPlan.coordinates.lng], 11);
  }
  setTimeout(() => map.invalidateSize(), 50);
}

function clearDynamicLayers(map) {
  map.eachLayer((layer) => {
    if (!(layer instanceof L.TileLayer)) map.removeLayer(layer);
  });
}

function renderTrips() {
  const container = $("tripList");
  const trips = state.session.trips || [];
  container.innerHTML = trips.length
    ? trips
        .map(
          (trip) => `
          <div class="col-md-6">
            <div class="trip-card">
              <div class="d-flex justify-content-between gap-3 flex-wrap">
                <div>
                  <div class="eyebrow">${escapeHtml(trip.status)}</div>
                  <h3>${escapeHtml(trip.destination)}</h3>
                  <div class="small-muted">${trip.days} days · ${escapeHtml(trip.start_date || "Flexible")} · ${formatMoney(trip.booking_total || trip.budget || 0, state.session.user?.currency || "USD")}</div>
                </div>
                <div class="d-flex gap-2">
                  <button class="btn btn-app btn-ghost btn-sm" type="button" data-view-trip="${trip.id}">Open</button>
                  <button class="btn btn-app btn-ghost btn-sm" type="button" data-delete-trip="${trip.id}">Delete</button>
                </div>
              </div>
            </div>
          </div>`
        )
        .join("")
    : `<div class="empty-state">No trips yet.</div>`;

  document.querySelectorAll("[data-view-trip]").forEach((button) =>
    button.addEventListener("click", () => {
      const trip = trips.find((item) => item.id === Number(button.dataset.viewTrip));
      if (trip) {
        state.currentPlan = trip.plan;
        saveCache();
        setPage("recommendation");
      }
    })
  );

  document.querySelectorAll("[data-delete-trip]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        const response = await api(`/api/trips/${button.dataset.deleteTrip}`, { method: "DELETE" });
        replaceSession(response.data);
        renderTrips();
        renderDashboard();
      } catch (error) {
        toast(error.message, "error");
      }
    })
  );
}

function renderWishlist() {
  const container = $("wishlistGrid");
  const items = state.session.wishlist || [];
  container.innerHTML = items.length
    ? items
        .map(
          (item) => `
          <div class="col-md-6 col-xl-4">
            <div class="trip-card">
              <div class="eyebrow">Saved destination</div>
              <h3>${escapeHtml(item.destination)}</h3>
              <div class="small-muted">${item.meta?.season ? escapeHtml(item.meta.season) : "Ready for later planning"}</div>
              <div class="d-flex gap-2 mt-3">
                <button class="btn btn-app btn-primary btn-sm" type="button" data-plan-wishlist="${item.destination}">Plan</button>
                <button class="btn btn-app btn-ghost btn-sm" type="button" data-delete-wishlist="${item.id}">Remove</button>
              </div>
            </div>
          </div>`
        )
        .join("")
    : `<div class="empty-state">No wishlist items yet.</div>`;

  document.querySelectorAll("[data-plan-wishlist]").forEach((button) =>
    button.addEventListener("click", () => {
      $("planDestination").value = button.dataset.planWishlist;
      requireAuth("planner");
    })
  );
  document.querySelectorAll("[data-delete-wishlist]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        const response = await api(`/api/wishlist/${button.dataset.deleteWishlist}`, { method: "DELETE" });
        replaceSession(response.data);
        renderWishlist();
        renderDashboard();
      } catch (error) {
        toast(error.message, "error");
      }
    })
  );
}

function notificationCard(notification) {
  return `<div class="notification-card"><strong>${escapeHtml(notification.title)}</strong><div class="small-muted">${escapeHtml(notification.description)}</div></div>`;
}

function renderNotifications() {
  $("notificationList").innerHTML = state.session.notifications.length
    ? state.session.notifications.map(notificationCard).join("")
    : `<div class="empty-state">No notifications.</div>`;
}

function renderPacking() {
  const items = state.session.packing || [];
  const destination = state.currentPlan?.destination || items[0]?.destination || "";
  if ($("packingDestination") && destination && !$("packingDestination").value) $("packingDestination").value = destination;
  if ($("packingDays") && state.currentPlan?.days) $("packingDays").value = state.currentPlan.days;
  const checked = items.filter((item) => item.checked).length;
  $("packingProgress").textContent = `${checked}/${items.length} packed`;
  $("packingSummary").textContent = items.length ? `Packing for ${items[0].destination}` : "Ready when you are";
  if (!items.length) {
    $("packingList").innerHTML = `<div class="empty-state">Generate a packing list from your destination, duration, and trip style.</div>`;
    return;
  }
  const groups = items.reduce((acc, item) => {
    acc[item.category] = acc[item.category] || [];
    acc[item.category].push(item);
    return acc;
  }, {});
  $("packingList").innerHTML = Object.entries(groups)
    .map(
      ([category, group]) => `
      <div class="packing-group">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <strong>${escapeHtml(category)}</strong>
          <span class="small-muted">${group.filter((item) => item.checked).length}/${group.length}</span>
        </div>
        ${group
          .map(
            (item) => `
            <label class="packing-item ${item.checked ? "checked" : ""}">
              <input type="checkbox" data-packing-id="${item.id}" ${item.checked ? "checked" : ""}>
              <span>${escapeHtml(item.item)}</span>
            </label>`
          )
          .join("")}
      </div>`
    )
    .join("");
  document.querySelectorAll("[data-packing-id]").forEach((input) =>
    input.addEventListener("change", async () => {
      try {
        const response = await api("/api/packing/toggle", {
          method: "POST",
          body: { id: Number(input.dataset.packingId), checked: input.checked },
        });
        replaceSession(response.data);
        renderPacking();
      } catch (error) {
        toast(error.message, "error");
      }
    })
  );
}

function renderCurrencyTools() {
  if (state.session.user?.currency) $("currencyFrom").value = state.session.user.currency;
  if (!$("translateSourceText").value && state.currentPlan) {
    $("translateSourceText").value = `${state.currentPlan.destination}: ${state.currentPlan.description}`;
  }
  if (!$("currencyResult").innerHTML.trim()) {
    $("currencyResult").innerHTML = `<div class="empty-state compact-empty">Enter an amount and convert using live/fallback exchange rates.</div>`;
  }
  if (!$("translateResult").innerHTML.trim()) {
    $("translateResult").innerHTML = `<div class="empty-state compact-empty">Translate important travel text before you go.</div>`;
  }
}

async function convertCurrencyTool() {
  try {
    const amount = Number($("currencyAmount").value || 0);
    if (amount <= 0) {
      toast("Enter a valid amount.", "error");
      return;
    }
    const response = await api(
      `/api/currency?amount=${encodeURIComponent(amount)}&from=${encodeURIComponent($("currencyFrom").value)}&to=${encodeURIComponent($("currencyTo").value)}`,
      { auth: false }
    );
    const data = response.data;
    $("currencyResult").innerHTML = `
      <div class="stack-item">
        <div class="eyebrow">Converted amount</div>
        <h3>${formatMoney(data.converted, data.to)}</h3>
        <div class="small-muted">1 ${escapeHtml(data.from)} = ${Number(data.rate).toFixed(4)} ${escapeHtml(data.to)} · Source: ${escapeHtml(data.source)}</div>
      </div>`;
  } catch (error) {
    toast(error.message, "error");
  }
}

async function translateTravelText() {
  const sourceText = $("translateSourceText").value.trim();
  if (!sourceText) {
    toast("Enter text to translate.", "error");
    return;
  }
  try {
    const response = await api(
      `/api/translate?text=${encodeURIComponent(sourceText)}&target=${encodeURIComponent($("translateTargetLang").value)}`,
      { auth: false }
    );
    $("translateResult").innerHTML = `
      <div class="stack-item">
        <div class="eyebrow">Translated text</div>
        <p class="mb-1">${escapeHtml(response.data.translated_text)}</p>
        <div class="small-muted">Target: ${escapeHtml(response.data.target_lang)} · Source: ${escapeHtml(response.data.source)}</div>
      </div>`;
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderProfile() {
  const user = state.session.user;
  if (!user) return;
  $("profileAvatar").innerHTML = user.avatar?.startsWith("data:image")
    ? `<img src="${user.avatar}" alt="Profile photo">`
    : escapeHtml(avatarLabel(user));
  $("profileName").textContent = user.name;
  $("profileEmail").textContent = user.email;
  $("profileNameInput").value = user.name;
  $("profilePhoneInput").value = user.phone || "";
  $("profileCityInput").value = user.city || "";
  $("profilePrefsInput").value = user.prefs || "";
  $("profileStats").innerHTML = [
    `${state.session.trips.length} trip(s)`,
    `${state.session.wishlist.length} wishlist item(s)`,
    `${state.session.reviews.length} review(s)`,
  ]
    .map((item) => `<div class="stack-item">${item}</div>`)
    .join("");
}

function renderSettings() {
  if (!state.session.user) return;
  $("settingsLanguage").value = state.session.user.language || "en";
  $("settingsCurrency").value = state.session.user.currency || "USD";
  $("settingsDarkMode").checked = state.theme === "dark";
}

function renderReviews() {
  $("reviewList").innerHTML = state.session.reviews.length
    ? state.session.reviews
        .map(
          (review) => `
          <div class="stack-item">
            <div class="d-flex justify-content-between gap-2">
              <strong>${escapeHtml(review.title)}</strong>
              <span class="status-pill">${review.rating}/5</span>
            </div>
            <div class="small-muted">${escapeHtml(review.destination)}</div>
            <p class="small-muted mb-0 mt-2">${escapeHtml(review.body)}</p>
          </div>`
        )
        .join("")
    : `<div class="empty-state">No reviews submitted yet.</div>`;
}

async function renderAdmin() {
  if (state.session.user?.role !== "admin") {
    $("adminOverview").innerHTML = `<div class="empty-state">Admin access only.</div>`;
    return;
  }
  try {
    const response = await api("/api/admin/overview");
    $("adminOverview").innerHTML = Object.entries(response.data)
      .map(([key, value]) => `<div class="col-md-3"><div class="metric-card"><span class="small-muted text-capitalize">${escapeHtml(key)}</span><strong>${value}</strong></div></div>`)
      .join("");
  } catch (error) {
    $("adminOverview").innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
  }
}

function replaceSession(sessionData) {
  state.session = sessionData;
  state.language = state.session.user?.language || state.language;
  updateNav();
  saveCache();
}

function formatMoney(amount, currency = "USD") {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch {
    return `${currency} ${Number(amount).toFixed(2)}`;
  }
}

async function submitSignup(event) {
  event.preventDefault();
  if ($("signupPassword").value !== $("signupConfirm").value) {
    toast("Passwords do not match.", "error");
    return;
  }
  try {
    const avatar = await readSingleImage($("signupAvatar"));
    const response = await api("/api/auth/signup", {
      method: "POST",
      auth: false,
      body: {
        name: $("signupName").value.trim(),
        phone: $("signupPhone").value.trim(),
        email: $("signupEmail").value.trim(),
        password: $("signupPassword").value,
        avatar,
      },
    });
    state.token = response.token;
    localStorage.setItem("smarttrip_token", state.token);
    replaceSession(response.data);
    toast("Account created successfully.");
    renderDashboard();
    setPage("dashboard");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitLogin(event) {
  event.preventDefault();
  try {
    const response = await api("/api/auth/login", {
      method: "POST",
      auth: false,
      body: {
        email: $("loginEmail").value.trim(),
        password: $("loginPassword").value,
      },
    });
    state.token = response.token;
    localStorage.setItem("smarttrip_token", state.token);
    replaceSession(response.data);
    toast("Logged in successfully.");
    renderDashboard();
    setPage("dashboard");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loginWithDemoProvider(provider) {
  try {
    const response = await api("/api/auth/social-demo", {
      method: "POST",
      auth: false,
      body: { provider, email: `${provider}.demo@smarttrip.local` },
    });
    state.token = response.token;
    localStorage.setItem("smarttrip_token", state.token);
    replaceSession(response.data);
    toast(`${provider} demo login successful.`);
    renderDashboard();
    setPage("dashboard");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loginWithOtpDemo() {
  const phone = window.prompt("Enter phone number for OTP demo login:");
  if (!phone) return;
  const otp = window.prompt("Enter OTP code (demo accepts any 4+ digit code):");
  if (!otp || otp.length < 4) {
    toast("Enter a valid OTP code.", "error");
    return;
  }
  try {
    const response = await api("/api/auth/otp-demo", {
      method: "POST",
      auth: false,
      body: { phone },
    });
    state.token = response.token;
    localStorage.setItem("smarttrip_token", state.token);
    replaceSession(response.data);
    toast("Phone OTP demo login successful.");
    renderDashboard();
    setPage("dashboard");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function requestPasswordResetDemo() {
  const email = window.prompt("Enter your account email:");
  if (!email) return;
  try {
    const response = await api("/api/auth/password-reset-demo", {
      method: "POST",
      auth: false,
      body: { email },
    });
    toast(response.data.message || "Reset request prepared.");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitPlanner(event) {
  event.preventDefault();
  const moods = [...document.querySelectorAll(".mood-chip.active")].map((chip) => chip.dataset.mood);
  const payload = {
    destination: $("planDestination").value.trim(),
    start_date: $("planStartDate").value,
    days: Number($("planDays").value),
    budget: Number($("planBudget").value),
    travelers: Number($("planTravelers").value),
    companion: $("planCompanion").value,
    accommodation: $("planAccommodation").value,
    notes: $("planNotes").value.trim(),
    moods,
    currency: state.session.user?.currency || "USD",
  };
  try {
    setStatus(text("planning"));
    toast(text("planning"));
    const response = await api("/api/plans/recommend", { method: "POST", body: payload, auth: false });
    state.currentPlan = response.data;
    state.booking = { hotel: null, flight: null, activities: [] };
    saveCache();
    renderRecommendation();
    renderItinerary();
    renderBooking();
    setPage("recommendation");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function quickPlanFromHome() {
  $("planDestination").value = $("homeDestination").value.trim();
  $("planDays").value = $("homeDays").value;
  $("planBudget").value = $("homeBudget").value;
  $("budgetLabel").textContent = formatMoney(Number($("planBudget").value), state.session.user?.currency || "USD");
  $("planTravelers").value = $("homeTravelers").value;
  $("planCompanion").value = $("homeCompanion").value;
  $("planStartDate").value = isoDate(14);
  if (!state.session.user) {
    setPage("signup");
    return;
  }
  setPage("planner");
}

async function saveCurrentPlan(status = "Saved") {
  if (!state.currentPlan) {
    toast("No active plan to save.", "error");
    return;
  }
  if (!state.session.user) {
    requireAuth("login");
    return;
  }
  try {
    const response = await api("/api/trips", {
      method: "POST",
      body: {
        status,
        booking_total: status === "Booked" ? bookingTotal() : 0,
        plan: state.currentPlan,
      },
    });
    replaceSession(response.data);
    toast(text("saved"));
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function addWishlist() {
  if (!state.currentPlan) return;
  if (!state.session.user) {
    requireAuth("login");
    return;
  }
  try {
    const response = await api("/api/wishlist", {
      method: "POST",
      body: {
        destination: state.currentPlan.destination,
        meta: { season: state.currentPlan.best_season },
      },
    });
    replaceSession(response.data);
    toast(text("saved"));
    renderWishlist();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitExpense(event) {
  event.preventDefault();
  try {
    const response = await api("/api/expenses", {
      method: "POST",
      body: {
        amount: Number($("expenseAmount").value),
        description: $("expenseDescription").value.trim(),
        category: $("expenseCategory").value,
        expense_date: $("expenseDate").value,
        trip_label: $("expenseTripLabel").value.trim(),
        receipt_name: $("expenseReceipt").value.trim(),
      },
    });
    replaceSession(response.data);
    event.target.reset();
    $("expenseDate").value = isoDate(0);
    toast("Expense added.");
    renderExpenses();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitProfile(event) {
  event.preventDefault();
  try {
    const avatar = await readSingleImage($("profileAvatarInput"));
    const response = await api("/api/profile", {
      method: "PUT",
      body: {
        name: $("profileNameInput").value.trim(),
        phone: $("profilePhoneInput").value.trim(),
        city: $("profileCityInput").value.trim(),
        prefs: $("profilePrefsInput").value.trim(),
        avatar: avatar || state.session.user.avatar,
        language: state.session.user.language,
        currency: state.session.user.currency,
        dark_mode: state.theme === "dark",
      },
    });
    replaceSession(response.data);
    toast(text("profileUpdated"));
    renderProfile();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitSettings(event) {
  event.preventDefault();
  try {
    const response = await api("/api/settings", {
      method: "PUT",
      body: {
        language: $("settingsLanguage").value,
        currency: $("settingsCurrency").value,
        dark_mode: $("settingsDarkMode").checked,
      },
    });
    replaceSession(response.data);
    state.language = $("settingsLanguage").value;
    setTheme($("settingsDarkMode").checked ? "dark" : "light");
    toast(text("settingsSaved"));
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitReview(event) {
  event.preventDefault();
  if (!state.session.user) {
    requireAuth("login");
    return;
  }
  try {
    const photos = await readMultipleImages($("reviewPhotos"));
    const response = await api("/api/reviews", {
      method: "POST",
      body: {
        destination: $("reviewDestination").value.trim(),
        title: $("reviewTitle").value.trim(),
        rating: Number($("reviewRating").value),
        body: $("reviewBody").value.trim(),
        photos,
      },
    });
    replaceSession(response.data);
    event.target.reset();
    toast("Review submitted.");
    renderReviews();
    renderDashboard();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function submitPacking(event) {
  event.preventDefault();
  try {
    const response = await api("/api/packing/generate", {
      method: "POST",
      body: {
        destination: $("packingDestination").value.trim(),
        days: Number($("packingDays").value),
        trip_type: $("packingType").value,
      },
    });
    replaceSession(response.data);
    toast("Packing list generated.");
    renderPacking();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function clearPackingList() {
  try {
    const response = await api("/api/packing", { method: "DELETE" });
    replaceSession(response.data);
    toast("Packing list cleared.");
    renderPacking();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function sendBuddyMessage(message, attachmentType = "") {
  if (!state.session.user || !state.currentBuddy) {
    requireAuth("login");
    return;
  }
  try {
    const response = await api("/api/chat/send", {
      method: "POST",
      body: {
        buddy_id: state.currentBuddy.id,
        message,
        attachment_type: attachmentType,
      },
    });
    replaceSession(response.data);
    renderChat();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function createGroupChatDemo() {
  if (!state.session.user) {
    requireAuth("login");
    return;
  }
  const matches = state.publicData.buddies
    .filter((buddy) => !state.currentPlan || buddy.destination.toLowerCase().includes(state.currentPlan.destination.split(",")[0].toLowerCase()) || buddy.match >= 88)
    .slice(0, 3);
  if (!matches.length) {
    toast("No compatible buddies found for a group chat.", "error");
    return;
  }
  try {
    for (const buddy of matches) {
      await api("/api/chat/send", {
        method: "POST",
        body: {
          buddy_id: buddy.id,
          message: `Group chat invite: let's coordinate ${state.currentPlan?.destination || buddy.destination} dates, budget, and route.`,
          attachment_type: "group-invite",
        },
      });
    }
    const latest = await api("/api/bootstrap", { auth: true });
    replaceSession(latest.data.session);
    state.currentBuddy = matches[0];
    renderChat();
    toast(`Group chat invite sent to ${matches.length} compatible travelers.`);
  } catch (error) {
    toast(error.message, "error");
  }
}

async function confirmPayment() {
  if (!state.currentPlan) return;
  if (!state.session.user) {
    requireAuth("login");
    return;
  }
  const activePane = document.querySelector(".payment-pane.active")?.dataset.pane || "card";
  if (activePane === "card") {
    const cardNumber = $("cardNumber").value.replace(/\D/g, "");
    if (!$("cardName").value.trim() || cardNumber.length < 12 || !$("cardExpiry").value.trim() || $("cardCvv").value.length < 3) {
      toast("Enter valid card details for demo checkout.", "error");
      return;
    }
  }
  if (activePane === "upi" && !/^[\w.-]+@[\w.-]+$/.test($("upiId").value.trim())) {
    toast("Enter a valid UPI ID.", "error");
    return;
  }
  if (activePane === "paypal" && !/\S+@\S+\.\S+/.test($("paypalEmail").value.trim())) {
    toast("Enter a valid PayPal email.", "error");
    return;
  }
  try {
    const response = await api("/api/bookings/confirm", {
      method: "POST",
      body: {
        total: bookingTotal(),
        plan: state.currentPlan,
      },
    });
    replaceSession(response.data);
    toast("Payment confirmed and trip booked.");
    renderTrips();
    renderDashboard();
    setPage("trips");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function sendAssistantMessage() {
  const input = $("assistantInput");
  const message = input.value.trim();
  if (!message) return;
  appendAssistantBubble(message, "user");
  input.value = "";
  try {
    const response = await api("/api/chat/assistant", {
      method: "POST",
      auth: false,
      body: { message, plan: state.currentPlan },
    });
    appendAssistantBubble(response.data.reply, "assistant");
  } catch (error) {
    appendAssistantBubble(error.message, "assistant");
  }
}

function appendAssistantBubble(message, sender) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${sender === "user" ? "user" : "assistant"}`;
  bubble.textContent = message;
  $("assistantMessages").appendChild(bubble);
  $("assistantMessages").scrollTop = $("assistantMessages").scrollHeight;
}

function bindEvents() {
  document.querySelectorAll("[data-nav]").forEach((node) =>
    node.addEventListener("click", (event) => {
      event.preventDefault();
      const page = node.dataset.nav;
      if (["dashboard", "planner", "trips", "expenses", "map", "wishlist", "notifications", "packing", "currency", "profile", "settings", "reviews", "admin"].includes(page)) {
        requireAuth(page);
      } else {
        setPage(page);
      }
    })
  );

  $("signupForm").addEventListener("submit", submitSignup);
  $("loginForm").addEventListener("submit", submitLogin);
  $("plannerForm").addEventListener("submit", submitPlanner);
  $("expenseForm").addEventListener("submit", submitExpense);
  $("profileForm").addEventListener("submit", submitProfile);
  $("settingsForm").addEventListener("submit", submitSettings);
  $("reviewForm").addEventListener("submit", submitReview);
  $("packingForm").addEventListener("submit", submitPacking);

  $("homePlanBtn").addEventListener("click", quickPlanFromHome);
  $("generatePlanBtn").addEventListener("click", () => setStatus(text("planning")));
  $("planBudget").addEventListener("input", () => {
    $("budgetLabel").textContent = formatMoney(Number($("planBudget").value), state.session.user?.currency || "USD");
  });

  $("savePlanBtn").addEventListener("click", () => saveCurrentPlan("Saved"));
  $("wishlistPlanBtn").addEventListener("click", addWishlist);
  $("sharePlanBtn").addEventListener("click", shareCurrentPlan);
  $("speakPlanBtn").addEventListener("click", speakPlanSummary);
  $("exportExpensesBtn").addEventListener("click", exportExpensesCsv);

  $("markAllReadBtn").addEventListener("click", async () => {
    try {
      const response = await api("/api/notifications/read-all", { method: "POST" });
      replaceSession(response.data);
      renderNotifications();
      renderDashboard();
    } catch (error) {
      toast(error.message, "error");
    }
  });

  $("clearNotificationsBtn").addEventListener("click", async () => {
    try {
      const response = await api("/api/notifications", { method: "DELETE" });
      replaceSession(response.data);
      renderNotifications();
      renderDashboard();
    } catch (error) {
      toast(error.message, "error");
    }
  });
  $("clearPackingBtn").addEventListener("click", clearPackingList);

  $("logoutBtn").addEventListener("click", async (event) => {
    event.preventDefault();
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {}
    state.token = "";
    localStorage.removeItem("smarttrip_token");
    state.session = { user: null, trips: [], expenses: [], wishlist: [], notifications: [], reviews: [], chat: {}, packing: [], analytics: {} };
    updateNav();
    renderHome();
    setPage("home");
  });

  $("assistantToggleBtn").addEventListener("click", () => $("assistantPanel").classList.add("open"));
  $("assistantCloseBtn").addEventListener("click", () => $("assistantPanel").classList.remove("open"));
  $("assistantSendBtn").addEventListener("click", sendAssistantMessage);
  $("assistantInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") sendAssistantMessage();
  });

  $("chatSendBtn").addEventListener("click", async () => {
    const value = $("chatInput").value.trim();
    if (!value) return;
    $("chatInput").value = "";
    await sendBuddyMessage(value);
  });
  $("chatInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      $("chatSendBtn").click();
    }
  });
  $("chatLocationBtn").addEventListener("click", async () => {
    if (!navigator.geolocation) {
      toast("Geolocation not supported.", "error");
      return;
    }
    navigator.geolocation.getCurrentPosition(async (position) => {
      const message = `My location: ${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}`;
      await sendBuddyMessage(message, "location");
    });
  });
  $("chatImageBtn").addEventListener("click", async () => sendBuddyMessage("Shared an image for trip context.", "image"));
  $("chatGroupBtn").addEventListener("click", createGroupChatDemo);

  $("buddyFilterBtn").addEventListener("click", renderBuddies);
  $("payNowBtn").addEventListener("click", confirmPayment);
  $("themeToggleBtn").addEventListener("click", toggleTheme);

  $("mapSearchBtn").addEventListener("click", searchMapPlaces);
  $("mapLocateBtn").addEventListener("click", locateOnMap);
  $("currencyConvertBtn").addEventListener("click", convertCurrencyTool);
  $("translateBtn").addEventListener("click", translateTravelText);

  $("forgotPasswordBtn").addEventListener("click", requestPasswordResetDemo);
  $("googleLoginBtn").addEventListener("click", () => loginWithDemoProvider("google"));
  $("otpLoginBtn").addEventListener("click", loginWithOtpDemo);

  $("cardNumber").addEventListener("input", () => {
    $("cardNumber").value = $("cardNumber").value.replace(/\D/g, "").replace(/(.{4})/g, "$1 ").trim().slice(0, 19);
  });
  document.querySelectorAll(".payment-tab").forEach((button) =>
    button.addEventListener("click", () => {
      document.querySelectorAll(".payment-tab").forEach((node) => node.classList.remove("active"));
      document.querySelectorAll(".payment-pane").forEach((node) => node.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`.payment-pane[data-pane="${button.dataset.pay}"]`).classList.add("active");
    })
  );

  $("planDestination").addEventListener("input", debounce(destinationLookup, 250));
  $("homeVoiceBtn").addEventListener("click", () => startVoiceInput("homeDestination"));
  $("planVoiceBtn").addEventListener("click", () => startVoiceInput("planDestination"));

  $("signupAvatar").addEventListener("change", async () => previewSingleImage("signupAvatar", "signupAvatarPreview"));
  $("profileAvatarInput").addEventListener("change", async () => previewSingleImage("profileAvatarInput", "profileAvatar"));
}

async function destinationLookup() {
  const query = $("planDestination").value.trim();
  if (!query) {
    $("destinationSuggestions").innerHTML = "";
    return;
  }
  try {
    const response = await api(`/api/search/destinations?q=${encodeURIComponent(query)}`, { auth: false });
    $("destinationSuggestions").innerHTML = response.data
      .map((item) => `<button class="suggestion-chip" type="button" data-suggestion="${escapeHtml(item.name)}">${escapeHtml(item.name)}</button>`)
      .join("");
    document.querySelectorAll("[data-suggestion]").forEach((button) =>
      button.addEventListener("click", () => {
        $("planDestination").value = button.dataset.suggestion;
        $("destinationSuggestions").innerHTML = "";
      })
    );
  } catch {
    $("destinationSuggestions").innerHTML = "";
  }
}

async function searchMapPlaces() {
  const query = $("mapSearch").value.trim();
  if (!query) return;
  try {
    const response = await api(`/api/location/search?q=${encodeURIComponent(query)}`, { auth: false });
    const results = response.data || [];
    $("mapPlaces").innerHTML = results.length
      ? results
          .map((item) => `<div class="stack-item"><strong>${escapeHtml(item.name)}</strong><div class="small-muted">${escapeHtml(item.type)}</div></div>`)
          .join("")
      : `<div class="empty-state compact-empty">No places found.</div>`;
    if (results.length && state.maps.global) {
      clearDynamicLayers(state.maps.global);
      const bounds = [];
      results.forEach((item) => {
        L.marker([item.lat, item.lng]).addTo(state.maps.global).bindPopup(item.name);
        bounds.push([item.lat, item.lng]);
      });
      state.maps.global.fitBounds(bounds, { padding: [30, 30] });
    }
  } catch (error) {
    toast(error.message, "error");
  }
}

function locateOnMap() {
  if (!navigator.geolocation) {
    toast("Geolocation not supported.", "error");
    return;
  }
  navigator.geolocation.getCurrentPosition((position) => {
    if (!state.maps.global) renderGlobalMap();
    clearDynamicLayers(state.maps.global);
    L.marker([position.coords.latitude, position.coords.longitude]).addTo(state.maps.global).bindPopup("You are here").openPopup();
    state.maps.global.setView([position.coords.latitude, position.coords.longitude], 12);
    $("mapPlaces").innerHTML = `<div class="stack-item"><strong>Your current location</strong><div class="small-muted">${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}</div></div>`;
  });
}

function exportExpensesCsv() {
  if (!state.session.expenses.length) {
    toast("No expenses to export.", "error");
    return;
  }
  const rows = ["date,category,description,amount,trip_label"];
  state.session.expenses.forEach((expense) => {
    rows.push(
      [expense.expense_date, expense.category, `"${expense.description.replaceAll('"', '""')}"`, expense.amount, `"${(expense.trip_label || "").replaceAll('"', '""')}"`].join(",")
    );
  });
  downloadFile("smarttrip-expenses.csv", rows.join("\n"), "text/csv");
  toast(text("exported"));
}

function shareCurrentPlan() {
  if (!state.currentPlan) return;
  const textToShare = `${state.currentPlan.destination} · ${state.currentPlan.days} days · ${state.currentPlan.budget_range}`;
  if (navigator.share) {
    navigator.share({ title: "SmartTrip AI plan", text: textToShare }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(textToShare);
    toast("Plan summary copied.");
  }
}

function speakPlanSummary() {
  if (!state.currentPlan || !("speechSynthesis" in window)) {
    toast("Speech output is not available in this browser.", "error");
    return;
  }
  const utterance = new SpeechSynthesisUtterance(
    `${state.currentPlan.destination}. ${state.currentPlan.days} day trip. Estimated budget ${state.currentPlan.budget_range}. Best season ${state.currentPlan.best_season}.`
  );
  speechSynthesis.cancel();
  speechSynthesis.speak(utterance);
}

function startVoiceInput(targetId) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    toast("Voice input is not supported in this browser.", "error");
    return;
  }
  const recognizer = new SpeechRecognition();
  recognizer.lang = "en-US";
  recognizer.interimResults = false;
  recognizer.onresult = (event) => {
    $(targetId).value = event.results[0][0].transcript;
    if (targetId === "planDestination") destinationLookup();
  };
  recognizer.onerror = () => toast("Could not capture voice input.", "error");
  recognizer.start();
}

function previewSingleImage(inputId, outputId) {
  const input = $(inputId);
  const output = $(outputId);
  if (!input.files?.[0]) return;
  const reader = new FileReader();
  reader.onload = () => {
    if (output.tagName === "DIV") output.innerHTML = `<img src="${reader.result}" alt="Preview">`;
    else output.textContent = "✓";
  };
  reader.readAsDataURL(input.files[0]);
}

function readSingleImage(input) {
  return new Promise((resolve) => {
    if (!input.files?.[0]) {
      resolve("");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(input.files[0]);
  });
}

function readMultipleImages(input) {
  return Promise.all([...input.files].map((file) => new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(file);
  })));
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function debounce(fn, wait) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function isoDate(offsetDays) {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().split("T")[0];
}

function applyInitialUI() {
  setTheme(state.theme);
  $("planStartDate").value = isoDate(14);
  $("expenseDate").value = isoDate(0);
  $("budgetLabel").textContent = formatMoney(Number($("planBudget").value), "USD");
  $("moodGrid").innerHTML = MOODS.map((mood) => `<button class="mood-chip" type="button" data-mood="${mood}">${mood}</button>`).join("");
  document.querySelectorAll(".mood-chip").forEach((chip) =>
    chip.addEventListener("click", () => chip.classList.toggle("active"))
  );
  appendAssistantBubble("Ask me about budgets, itineraries, safety, routing, weather, or destination fit.", "assistant");
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/js/sw.js").catch(() => {});
  }
}

function installGlobalErrorLogging() {
  window.addEventListener("error", (event) => {
    api("/api/logs/client", {
      method: "POST",
      auth: false,
      body: { type: "error", message: event.message, source: event.filename, line: event.lineno, column: event.colno },
    }).catch(() => {});
  });
  window.addEventListener("unhandledrejection", (event) => {
    api("/api/logs/client", {
      method: "POST",
      auth: false,
      body: { type: "promise", message: String(event.reason) },
    }).catch(() => {});
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  applyInitialUI();
  bindEvents();
  installGlobalErrorLogging();
  registerServiceWorker();
  await bootstrap();
  setPage(state.session.user ? "dashboard" : "home");
  setTimeout(() => $("splash").classList.add("hidden"), 900);
});
