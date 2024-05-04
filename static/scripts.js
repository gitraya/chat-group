"use strict";

const socket = io();
let page = 1;
const pageSize = 20;
let isEndOfMessages = false;
let isOnLoadMessages = false;

const addNewMessage = (message, container, isNew = true) => {
  const newDivider = document.createElement("li");
  newDivider.className = "flex justify-center items-center";
  newDivider.innerHTML = `
        <hr class="w-full border border-slate-500" />
        <p class="text-xs font-semibold text-slate-300 shrink-0 px-3">${message.start_date_at}</p>
        <hr class="w-full border border-slate-500" />
        `;

  const newMessage = document.createElement("li");
  newMessage.className = "flex gap-4";
  newMessage.innerHTML = `
        ${
          message.profile_url
            ? `<img src="${message.profile_url}" alt="Profile Picture" class="w-9 h-9 rounded-lg shrink-0 object-cover">`
            : `<div class="w-9 h-9 bg-slate-300 rounded-lg flex items-center justify-center shrink-0"><i class="fa-solid fa-user" style="color: black"></i></div>`
        }
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-lg text-slate-300">${
              message.name
            }</span>
            <span class="text-slate-400 text-sm">${message.created_at}</span>
          </div>
          <p class="text-lg text-gray-100">${message.message}</p>
        </div>
        `;

  if (isNew) {
    if (message.start_date_at) {
      container.insertBefore(newDivider, container.firstChild);
    }

    container.insertBefore(newMessage, container.firstChild);
  }

  if (!isNew) {
    container.appendChild(newMessage);

    if (message.start_date_at) {
      container.appendChild(newDivider);
    }
  }
};

function goBack() {
  window.history.back();
}

function resetRoom() {
  socket.emit("reset_room");
}

function submitMessage(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const message = formData.get("message");

  socket.emit("new_message", message);
  form.reset();
}

function autoRemoveToast() {
  setInterval(() => {
    const toast = document.getElementById("toast-default");
    if (!toast) return;

    setTimeout(() => {
      toast.remove();
    }, 5000);
  }, 100);
}

function animateSubmitButton() {
  const buttons = document.querySelectorAll('button[type="submit"]');
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const form = button.parentElement;
      if (button.classList.contains("no-loading") || !form.checkValidity()) {
        return;
      }

      button.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i>`;
    });
  });
}

function listenMoreMessages() {
  const chatMessages = document.getElementById("message-list");
  if (!chatMessages) return;

  chatMessages.addEventListener("scroll", () => {
    if (
      Math.abs(
        chatMessages.scrollHeight -
          Math.abs(chatMessages.scrollTop) -
          chatMessages.clientHeight
      ) < 1
    ) {
      if (isEndOfMessages || isOnLoadMessages) return;

      page += 1;
      isOnLoadMessages = true;

      // Add loading indicator
      const loadingLi = document.createElement("li");
      loadingLi.className =
        "loading-indicator flex justify-center items-center";
      loadingLi.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i>`;
      chatMessages.appendChild(loadingLi);

      // Fetch more messages
      fetch(`/messages?page=${page}&pageSize=${pageSize}`)
        .then((response) => response.json())
        .then((data) => {
          const chatMessages = document.querySelector("#message-list");
          const loadings = chatMessages.querySelectorAll(".loading-indicator");

          if (!data.items || data.items.length === 0) {
            isEndOfMessages = true;
            isOnLoadMessages = false;

            if (loadings && loadings.length > 0) {
              loadings.forEach((loading) => loading.remove());
            }

            return;
          }

          const messages = data.items;

          if (loadings && loadings.length > 0) {
            loadings.forEach((loading) => loading.remove());
          }

          messages.forEach((message) => {
            addNewMessage(message, chatMessages, false);
          });

          isOnLoadMessages = false;
        });
    }
  });
}

window.onload = function () {
  resetRoom();
  autoRemoveToast();
  animateSubmitButton();
  listenMoreMessages();
};
