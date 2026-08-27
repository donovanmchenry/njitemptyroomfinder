const state = {
  metadata: null,
  buildings: [],
  results: null,
  activeTab: "available",
  controller: null,
};

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const elements = {
  form: document.querySelector("#searchForm"),
  dayButtons: [...document.querySelectorAll("[data-day]")],
  startTime: document.querySelector("#timeInput"),
  duration: document.querySelector("#durationSelect"),
  building: document.querySelector("#buildingSelect"),
  roomQuery: document.querySelector("#roomQuery"),
  sort: document.querySelector("#sortSelect"),
  useNow: document.querySelector("#useNowButton"),
  searchButton: document.querySelector("#searchButton"),
  themeToggle: document.querySelector("#themeToggle"),
  termLabel: document.querySelector("#termLabel"),
  querySummary: document.querySelector("#querySummary"),
  selectionSummary: document.querySelector("#selectionSummary"),
  availableTab: document.querySelector('[data-result-tab="available"]'),
  unavailableTab: document.querySelector('[data-result-tab="unavailable"]'),
  availableCount: document.querySelector("#availableTabCount"),
  unavailableCount: document.querySelector("#unavailableTabCount"),
  totalStat: document.querySelector("#totalRooms"),
  availableStat: document.querySelector("#availableRooms"),
  occupiedStat: document.querySelector("#occupiedRooms"),
  startsSoonStat: document.querySelector("#startsSoonRooms"),
  loadingState: document.querySelector("#loadingState"),
  errorState: document.querySelector("#errorState"),
  errorMessage: document.querySelector("#errorMessage"),
  emptyState: document.querySelector("#emptyState"),
  emptyTitle: document.querySelector("#emptyTitle"),
  emptyMessage: document.querySelector("#emptyMessage"),
  roomGrid: document.querySelector("#roomGrid"),
  roomDialog: document.querySelector("#scheduleDialog"),
  dialogTitle: document.querySelector("#dialogRoomName"),
  dialogSubtitle: document.querySelector("#dialogSubtitle"),
  dialogSchedule: document.querySelector("#dialogSchedule"),
  closeDialog: document.querySelector("#closeDialog"),
};

function selectedDay() {
  return elements.dayButtons.find((button) => button.classList.contains("active"))?.dataset.day || "Monday";
}

function selectDay(day) {
  const validDay = DAYS.includes(day) ? day : "Monday";
  elements.dayButtons.forEach((button) => {
    const selected = button.dataset.day === validDay;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  updateQuerySummary();
}

function setCurrentTime() {
  const now = new Date();
  const day = DAYS[(now.getDay() + 6) % 7];
  const roundedMinutes = Math.ceil(now.getMinutes() / 5) * 5;
  let hours = now.getHours();
  let minutes = roundedMinutes;
  if (minutes === 60) {
    hours += 1;
    minutes = 0;
  }
  if (hours >= 24) {
    hours = 23;
    minutes = 55;
  }
  selectDay(day);
  elements.startTime.value = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
  updateQuerySummary();
}

function formatTime(value) {
  if (!value) return "";
  const [hourText, minuteText] = value.split(":");
  const hour = Number(hourText);
  const suffix = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${minuteText} ${suffix}`;
}

function formatDuration(minutes) {
  const value = Number(minutes);
  if (value < 60) return `${value} min`;
  if (value % 60 === 0) return `${value / 60} hr`;
  return `${Math.floor(value / 60)} hr ${value % 60} min`;
}

function updateQuerySummary() {
  const buildingText = elements.building.selectedOptions[0]?.textContent || "All buildings";
  elements.selectionSummary.textContent = `${selectedDay()} · ${formatTime(elements.startTime.value)} · ${formatDuration(elements.duration.value)} · ${buildingText}`;
}

function setView(name) {
  for (const element of [elements.loadingState, elements.errorState, elements.emptyState, elements.roomGrid]) {
    element.hidden = true;
  }
  if (name === "loading") elements.loadingState.hidden = false;
  if (name === "error") elements.errorState.hidden = false;
  if (name === "empty") elements.emptyState.hidden = false;
  if (name === "results") elements.roomGrid.hidden = false;
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function occupancyText(room) {
  if (room.available) {
    return room.available_until ? `Free until ${formatTime(room.available_until)}` : "Free for the rest of the day";
  }
  if (room.reason === "starts_soon") {
    return `Class starts at ${formatTime(room.blocking_class?.start_time)}`;
  }
  return `In use until ${formatTime(room.blocking_class?.end_time)}`;
}

function createRoomCard(room) {
  const card = makeElement("article", "room-card");
  const header = makeElement("div", "room-card-header");
  const roomInfo = makeElement("div", "room-identity");
  roomInfo.append(makeElement("h3", "", room.room));
  roomInfo.append(makeElement("p", "", room.building));

  const badge = makeElement(
    "span",
    `status-badge ${room.available ? "available" : room.reason === "starts_soon" ? "starts-soon" : "occupied"}`,
    room.available ? "Available" : room.reason === "starts_soon" ? "Starts soon" : "In use",
  );
  header.append(roomInfo, badge);

  const status = makeElement("div", "availability-line");
  status.append(makeElement("strong", "", occupancyText(room)));
  status.append(makeElement("span", "", room.available && room.free_minutes ? `${formatDuration(room.free_minutes)} open` : ""));
  const detail = makeElement("div", "class-detail");

  if (room.available && room.next_class) {
    detail.append(makeElement("span", "detail-label", "Next class"));
    detail.append(makeElement("p", "course-line", room.next_class.course));
    detail.append(makeElement("p", "time-line", formatTime(room.next_class.start_time)));
  } else if (!room.available && room.blocking_class) {
    detail.append(makeElement("span", "detail-label", room.reason === "starts_soon" ? "Upcoming" : "Current class"));
    detail.append(makeElement("p", "course-line", room.blocking_class.course));
    detail.append(makeElement("p", "time-line", `${formatTime(room.blocking_class.start_time)}–${formatTime(room.blocking_class.end_time)}`));
  } else {
    detail.append(makeElement("span", "detail-label", "Schedule"));
    detail.append(makeElement("p", "course-line", "No more classes listed today"));
  }

  const footer = makeElement("div", "room-card-footer");
  const scheduleButton = makeElement("button", "text-button", "View weekly schedule");
  scheduleButton.type = "button";
  scheduleButton.addEventListener("click", () => openRoomSchedule(room.room));

  footer.append(scheduleButton);
  card.append(header, status, detail, footer);
  return card;
}

function renderResults() {
  if (!state.results) return;
  const rooms = state.results[`${state.activeTab}_rooms`] || [];
  elements.availableTab.classList.toggle("active", state.activeTab === "available");
  elements.unavailableTab.classList.toggle("active", state.activeTab === "unavailable");
  elements.availableTab.setAttribute("aria-selected", String(state.activeTab === "available"));
  elements.unavailableTab.setAttribute("aria-selected", String(state.activeTab === "unavailable"));
  elements.roomGrid.replaceChildren();

  if (!rooms.length) {
    elements.emptyTitle.textContent = state.activeTab === "available" ? "No rooms are free" : "No unavailable rooms";
    elements.emptyMessage.textContent = state.activeTab === "available"
      ? "Try a shorter stay, another building, or a different start time."
      : "Every matching room is available for the selected time."
    setView("empty");
    return;
  }

  rooms.forEach((room) => elements.roomGrid.append(createRoomCard(room)));
  setView("results");
}

function updateCounts() {
  const summary = state.results.summary;
  elements.availableCount.textContent = summary.available;
  elements.unavailableCount.textContent = summary.occupied + summary.starts_soon;
  elements.totalStat.textContent = summary.total_rooms;
  elements.availableStat.textContent = summary.available;
  elements.occupiedStat.textContent = summary.occupied;
  elements.startsSoonStat.textContent = summary.starts_soon;
  elements.querySummary.textContent = `${state.results.day} · ${formatTime(state.results.start_time)}–${formatTime(state.results.end_time)} · ${summary.total_rooms} matching rooms`;
}

async function searchRooms() {
  state.controller?.abort();
  state.controller = new AbortController();
  setView("loading");
  elements.searchButton.disabled = true;
  elements.searchButton.textContent = "Checking…";

  const payload = {
    day: selectedDay(),
    time: elements.startTime.value,
    duration_minutes: Number(elements.duration.value),
    building: elements.building.value,
    query: elements.roomQuery.value.trim(),
    sort: elements.sort.value,
  };

  try {
    const response = await fetch("/api/available-rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: state.controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The room data could not be loaded.");
    state.results = data;
    updateCounts();
    renderResults();
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message;
    setView("error");
  } finally {
    elements.searchButton.disabled = false;
    elements.searchButton.textContent = "Find rooms";
  }
}

function renderRoomSchedule(room, schedule) {
  elements.dialogTitle.textContent = room;
  elements.dialogSubtitle.textContent = `${state.metadata?.term_name || "Current term"} weekly schedule`;
  elements.dialogSchedule.replaceChildren();

  DAYS.forEach((day) => {
    const daySection = makeElement("section", "day-schedule");
    daySection.append(makeElement("h3", "", day));
    const slots = makeElement("div", "schedule-slots");
    const classes = schedule[day] || [];
    if (!classes.length) {
      slots.append(makeElement("p", "no-classes", "No classes"));
    } else {
      classes.forEach((meeting) => {
        const row = makeElement("div", "schedule-slot");
        row.append(makeElement("time", "", `${formatTime(meeting.start_time)}–${formatTime(meeting.end_time)}`));
        const course = makeElement("div", "");
        course.append(makeElement("strong", "", meeting.course));
        if (meeting.title) course.append(makeElement("span", "", meeting.title));
        row.append(course);
        slots.append(row);
      });
    }
    daySection.append(slots);
    elements.dialogSchedule.append(daySection);
  });
}

async function openRoomSchedule(room) {
  elements.dialogTitle.textContent = room;
  elements.dialogSubtitle.textContent = "Loading schedule…";
  elements.dialogSchedule.replaceChildren();
  elements.roomDialog.showModal();
  try {
    const response = await fetch(`/api/room/${encodeURIComponent(room)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Schedule unavailable.");
    renderRoomSchedule(data.room, data.schedule);
  } catch (error) {
    elements.dialogSubtitle.textContent = error.message;
  }
}

async function loadMetadata() {
  const [metaResponse, buildingsResponse] = await Promise.all([
    fetch("/api/meta"),
    fetch("/api/buildings"),
  ]);
  if (!metaResponse.ok || !buildingsResponse.ok) throw new Error("Room data is unavailable.");
  const metaPayload = await metaResponse.json();
  const buildingPayload = await buildingsResponse.json();
  state.metadata = metaPayload.metadata;
  state.buildings = buildingPayload.buildings;
  elements.termLabel.textContent = state.metadata.term_name;

  state.buildings.forEach((building) => {
    const option = document.createElement("option");
    option.value = building.code;
    option.textContent = `${building.code} (${building.room_count})`;
    elements.building.append(option);
  });
  updateQuerySummary();
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle("dark");
  localStorage.setItem("empty-room-theme", isDark ? "dark" : "light");
  updateThemeButton(isDark);
}

function updateThemeButton(isDark) {
  elements.themeToggle.setAttribute("aria-label", isDark ? "Use light mode" : "Use dark mode");
  elements.themeToggle.title = isDark ? "Use light mode" : "Use dark mode";
}

function bindEvents() {
  elements.dayButtons.forEach((button) => button.addEventListener("click", () => selectDay(button.dataset.day)));
  elements.startTime.addEventListener("change", updateQuerySummary);
  elements.duration.addEventListener("change", updateQuerySummary);
  elements.building.addEventListener("change", updateQuerySummary);
  elements.sort.addEventListener("change", () => state.results && searchRooms());
  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    searchRooms();
  });
  elements.useNow.addEventListener("click", () => {
    setCurrentTime();
    searchRooms();
  });
  elements.availableTab.addEventListener("click", () => {
    state.activeTab = "available";
    renderResults();
  });
  elements.unavailableTab.addEventListener("click", () => {
    state.activeTab = "unavailable";
    renderResults();
  });
  elements.themeToggle.addEventListener("click", toggleTheme);
  elements.closeDialog.addEventListener("click", () => elements.roomDialog.close());
  elements.roomDialog.addEventListener("click", (event) => {
    if (event.target === elements.roomDialog) elements.roomDialog.close();
  });
}

async function initialize() {
  bindEvents();
  updateThemeButton(document.documentElement.classList.contains("dark"));
  setCurrentTime();
  try {
    await loadMetadata();
    await searchRooms();
  } catch (error) {
    elements.errorMessage.textContent = error.message;
    setView("error");
  }
}

initialize();
