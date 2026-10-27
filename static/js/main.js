function showLogoutModal(event) {
  if (event) event.preventDefault();
  document.getElementById("logoutModal").style.display = "flex";
}

function closeLogoutModal() {
  document.getElementById("logoutModal").style.display = "none";
}

function confirmLogout() {
  window.location.href = "/logout";
}

// Close modal when clicking outside
window.onclick = function (event) {
  const modal = document.getElementById("logoutModal");
  if (event.target == modal) {
    closeLogoutModal();
  }
};
// Notification System
function toggleNotifs(event) {
  if (event) event.stopPropagation();
  const dropdown = document.getElementById("notif-dropdown");
  if (!dropdown) return;

  const isVisible = dropdown.style.display === "block";

  // Close other dropdowns if any
  document
    .querySelectorAll(".notif-dropdown")
    .forEach((d) => (d.style.display = "none"));

  if (!isVisible) {
    dropdown.style.display = "flex";
    dropdown.style.flexDirection = "column";
    fetchNotifications();
  } else {
    dropdown.style.display = "none";
  }
}

async function fetchNotifications() {
  try {
    const response = await fetch("/api/notifications");
    const data = await response.json();
    const list = document.getElementById("notif-list");
    const badge = document.getElementById("notif-badge");

    const unreadCount = data.notifications.filter((n) => !n.is_read).length;
    if (unreadCount > 0) {
      badge.innerText = unreadCount;
      badge.style.display = "flex";
    } else {
      badge.style.display = "none";
    }

    if (data.notifications.length === 0) {
      list.innerHTML = '<div class="notif-empty">No notifications yet</div>';
      return;
    }

    list.innerHTML = data.notifications
      .map(
        (n) => `
            <div class="notif-item ${n.is_read ? "" : "unread"}" onclick="markAsRead('${n._id}', '${n.link}')" style="cursor: pointer; padding: 1rem; border-bottom: 1px solid rgba(0,0,0,0.05);">
                <span class="title" style="font-weight: 600; font-size: 0.9rem; color: var(--primary); display: block; margin-bottom: 0.3rem;">${n.title}</span>
                <span class="msg" style="font-size: 0.85rem; color: var(--text-muted); display: block; margin-bottom: 0.4rem; line-height: 1.4;">${n.message}</span>
                <span class="time" style="font-size: 0.75rem; color: #94a3b8; display: block;">${n.created_at}</span>
            </div>
        `,
      )
      .join("");
  } catch (err) {
    console.error("Error fetching notifications:", err);
  }
}

async function markAsRead(id, link) {
  try {
    await fetch(`/api/notifications/read/${id}`, { method: "POST" });
    window.location.href = link;
  } catch (err) {
    window.location.href = link;
  }
}

// Close dropdowns on click outside - with proper z-index handling
document.addEventListener("click", (e) => {
  const dropdown = document.getElementById("notif-dropdown");
  const notifBtn = document.querySelector(".notif-btn");

  if (
    dropdown &&
    notifBtn &&
    !notifBtn.contains(e.target) &&
    !dropdown.contains(e.target)
  ) {
    dropdown.style.display = "none";
  }
});

// Prevent notification dropdown from closing when clicking inside it
document.addEventListener(
  "click",
  (e) => {
    if (e.target.closest(".notif-dropdown")) {
      e.stopPropagation();
    }
  },
  true,
);

// Initial fetch for badge
if (document.getElementById("notif-badge")) {
  fetchNotifications();
  // Poll every minute
  setInterval(fetchNotifications, 60000);
}
