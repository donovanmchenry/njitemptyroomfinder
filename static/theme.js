try {
  const theme = localStorage.getItem("empty-room-theme") || "dark";
  document.documentElement.classList.toggle("dark", theme === "dark");
} catch (_) {
  document.documentElement.classList.add("dark");
}
