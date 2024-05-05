"use strict";
let page = 1;
const pageSize = 20;
let isEndOfMessages = false;
let isOnLoadMessages = false;

function resetRoom() {
  socket.emit("reset_room");
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

function goBack() {
  window.history.back();
}

function submitMessage(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const message = formData.get("message");

  socket.emit("new_message", message);
  form.reset();
}

window.onload = function () {
  resetRoom();
  autoRemoveToast();
  animateSubmitButton();
  listenMoreMessages();
};
