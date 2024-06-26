"use strict";
const socket = io();
const exeptionalPages = ["apology", "profile", "password", "register", "login"];

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

socket.on("connect", function () {
  const body = document.querySelector("body");
  const newToast = document.createElement("div");
  newToast.id = "toast-default";
  newToast.className =
    "fixed border border-green-800 flex items-center w-full max-w-xs p-4 text-gray-300 bg-slate-800 rounded-lg shadow top-5 right-5 gap-2";
  newToast.role = "alert";
  newToast.innerHTML = `<div class="inline-flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-lg bg-blue-800 text-blue-200"><svg class="w-4 h-4" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 18 20"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.147 15.085a7.159 7.159 0 0 1-6.189 3.307A6.713 6.713 0 0 1 3.1 15.444c-2.679-4.513.287-8.737.888-9.548A4.373 4.373 0 0 0 5 1.608c1.287.953 6.445 3.218 5.537 10.5 1.5-1.122 2.706-3.01 2.853-6.14 1.433 1.049 3.993 5.395 1.757 9.117Z"/></svg><span class="sr-only">Fire icon</span></div><div class="ms-2 text-sm font-normal break-words">You are online!</div><button type="button" class="ms-auto -mx-1.5 -my-1.5 rounded-lg focus:ring-2 focus:ring-gray-300 p-1.5 inline-flex items-center justify-center h-8 w-8 text-gray-500 hover:text-white bg-gray-800 hover:bg-gray-700" data-dismiss-target="#toast-default" aria-label="Close"><span class="sr-only">Close</span><svg class="w-3 h-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 14 14"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"/></svg></button>`;

  if (!exeptionalPages.some((page) => window.location.href.includes(page))) {
    body.appendChild(newToast);
  }
});

socket.on("disconnect", function () {
  const body = document.querySelector("body");
  const newToast = document.createElement("div");
  newToast.id = "toast-default";
  newToast.className =
    "fixed border border-red-800 flex items-center w-full max-w-xs p-4 text-gray-300 bg-slate-800 rounded-lg shadow top-5 right-5 gap-2";
  newToast.role = "alert";
  newToast.innerHTML = `<div class="inline-flex items-center justify-center flex-shrink-0 w-8 h-8 text-red-500 bg-red-100 rounded-lg dark:bg-red-800 dark:text-red-200"><svg class="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20"><path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5Zm3.707 11.793a1 1 0 1 1-1.414 1.414L10 11.414l-2.293 2.293a1 1 0 0 1-1.414-1.414L8.586 10 6.293 7.707a1 1 0 0 1 1.414-1.414L10 8.586l2.293-2.293a1 1 0 0 1 1.414 1.414L11.414 10l2.293 2.293Z"/></svg><span class="sr-only">Error icon</span></div><div class="ms-2 text-sm font-normal break-words">You are offline!</div><button type="button" class="ms-auto -mx-1.5 -my-1.5 rounded-lg focus:ring-2 focus:ring-gray-300 p-1.5 inline-flex items-center justify-center h-8 w-8 text-gray-500 hover:text-white bg-gray-800 hover:bg-gray-700" data-dismiss-target="#toast-default" aria-label="Close"><span class="sr-only">Close</span><svg class="w-3 h-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 14 14"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"/></svg></button>`;

  if (!exeptionalPages.some((page) => window.location.href.includes(page))) {
    body.appendChild(newToast);
  }
});

socket.on("new_message", function (json) {
  const message = JSON.parse(json);
  const chatMessages = document.querySelector("#message-list");

  if (chatMessages.innerHTML.includes("empty-messages")) {
    chatMessages.innerHTML = "";
  }

  addNewMessage(message, chatMessages);
  chatMessages.scrollTop = chatMessages.scrollHeight;
});

socket.on("new_member", function (json) {
  const member = JSON.parse(json);
  const memberList = document.querySelectorAll(".member-list");
  const newLi = document.createElement("li");
  newLi.className = "flex items-center text-slate-200";
  newLi.innerHTML = `${
    member.profile_url
      ? ` <img src="${member.profile_url}" alt="Profile Picture" class="w-9 h-9 rounded object-cover shrink-0">`
      : `<div class="w-9 h-9 bg-slate-300 rounded flex items-center justify-center"><i class="fa-solid fa-user" style="color: black"></i></div>`
  }<span class="ml-3 font-semibold text-lg">${member.name}</span>`;

  memberList.forEach((list) => {
    list.insertBefore(newLi, list.firstChild);
  });
});
