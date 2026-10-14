try {
  const theme = localStorage.getItem("empty-room-theme") || "light";
  document.documentElement.classList.toggle("dark", theme === "dark");
} catch (_) {
  document.documentElement.classList.remove("dark");
}
