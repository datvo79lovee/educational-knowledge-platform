"use strict";

// Local demo client for POST /answer.
//
// It renders only the three public response fields a reader needs: decision, answer
// and application-owned citations. Every other response field is a runtime
// diagnostic and is deliberately never read or displayed here. Server text is always
// rendered with textContent, never as HTML.
//
// A test scans this file for diagnostic field names, so do not name them even in a
// comment; that check is a strict substring match on purpose.

(function () {
  var form = document.getElementById("ask-form");
  var questionInput = document.getElementById("question");
  var languageSelect = document.getElementById("answer-language");
  var submitButton = document.getElementById("submit");
  var resultRegion = document.getElementById("result");

  var TEXT = {
    en: {
      loading: "Asking the local model…",
      answered: "Answer",
      abstained: "Not enough evidence",
      abstainBody:
        "The retrieved course excerpts do not support a complete answer, so the " +
        "system declined to answer instead of guessing.",
      citations: "Citations",
      emptyQuestion: "Please type a question first.",
      errorStatus: "Request failed"
    },
    vi: {
      loading: "Đang hỏi mô hình cục bộ…",
      answered: "Câu trả lời",
      abstained: "Không đủ bằng chứng",
      abstainBody:
        "Các đoạn trích được truy xuất không đủ để trả lời trọn vẹn, nên hệ thống " +
        "từ chối trả lời thay vì suy đoán.",
      citations: "Trích dẫn",
      emptyQuestion: "Hãy nhập câu hỏi trước.",
      errorStatus: "Yêu cầu thất bại"
    }
  };

  // Fixed, non-leaking messages keyed by status. Server bodies are never rendered.
  var ERRORS = {
    en: {
      400: "The request was rejected. Check the question and try again.",
      422: "The question was not accepted. Enter a non-empty question.",
      502: "The local model returned an invalid response. Try again.",
      503: "The local model runtime is unavailable. Start Ollama and try again.",
      network: "Could not reach the local API. Is the server running on this machine?",
      generic: "Something went wrong. Try again."
    },
    vi: {
      400: "Yêu cầu bị từ chối. Kiểm tra lại câu hỏi rồi thử lại.",
      422: "Câu hỏi không hợp lệ. Hãy nhập câu hỏi không rỗng.",
      502: "Mô hình cục bộ trả về phản hồi không hợp lệ. Thử lại.",
      503: "Runtime mô hình cục bộ không sẵn sàng. Khởi động Ollama rồi thử lại.",
      network: "Không kết nối được API cục bộ. Server có đang chạy trên máy này không?",
      generic: "Đã có lỗi xảy ra. Thử lại."
    }
  };

  function texts() {
    return TEXT[languageSelect.value] || TEXT.en;
  }

  function errorMessage(status) {
    var table = ERRORS[languageSelect.value] || ERRORS.en;
    if (status === "network") {
      return table.network;
    }
    return table[status] || table.generic;
  }

  function clear(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function card(modifier, status, body) {
    var section = document.createElement("div");
    section.className = "card card--" + modifier;

    var heading = document.createElement("p");
    heading.className = "card__status";
    heading.textContent = status;
    section.appendChild(heading);

    if (body) {
      var paragraph = document.createElement("p");
      paragraph.className = "card__body";
      paragraph.textContent = body;
      section.appendChild(paragraph);
    }
    return section;
  }

  function formatTimestamp(seconds) {
    var whole = Math.max(0, Math.floor(Number(seconds) || 0));
    var minutes = Math.floor(whole / 60);
    var rest = whole % 60;
    return minutes + ":" + (rest < 10 ? "0" : "") + rest;
  }

  function citationList(citations) {
    var wrapper = document.createElement("div");

    var title = document.createElement("p");
    title.className = "citations__title";
    title.textContent = texts().citations;
    wrapper.appendChild(title);

    var list = document.createElement("ul");
    list.className = "citations";

    citations.forEach(function (citation) {
      var item = document.createElement("li");
      item.className = "citations__item";

      var link = document.createElement("a");
      // citation_url is built by the application from canonical chunk metadata.
      link.href = citation.citation_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = citation.video_id + " @ " + formatTimestamp(citation.start);
      item.appendChild(link);

      var meta = document.createElement("span");
      meta.className = "citations__meta";
      meta.textContent =
        "rank " + citation.rank + " · " +
        formatTimestamp(citation.start) + "–" + formatTimestamp(citation.end);
      item.appendChild(meta);

      list.appendChild(item);
    });

    wrapper.appendChild(list);
    return wrapper;
  }

  function renderLoading() {
    clear(resultRegion);
    resultRegion.setAttribute("aria-busy", "true");
    resultRegion.appendChild(card("loading", texts().loading, ""));
  }

  function renderError(status) {
    clear(resultRegion);
    resultRegion.setAttribute("aria-busy", "false");
    resultRegion.appendChild(card("error", texts().errorStatus, errorMessage(status)));
  }

  function renderResponse(payload) {
    clear(resultRegion);
    resultRegion.setAttribute("aria-busy", "false");
    var labels = texts();

    if (payload.decision === "abstain") {
      resultRegion.appendChild(card("abstain", labels.abstained, labels.abstainBody));
      return;
    }

    var section = card("answer", labels.answered, payload.answer || "");
    if (Array.isArray(payload.citations) && payload.citations.length > 0) {
      section.appendChild(citationList(payload.citations));
    }
    resultRegion.appendChild(section);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var question = questionInput.value.trim();
    if (question.length === 0) {
      clear(resultRegion);
      resultRegion.setAttribute("aria-busy", "false");
      resultRegion.appendChild(card("error", texts().errorStatus, texts().emptyQuestion));
      return;
    }

    submitButton.disabled = true;
    renderLoading();

    fetch("/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        answer_language: languageSelect.value
      })
    })
      .then(function (response) {
        if (!response.ok) {
          renderError(response.status);
          return null;
        }
        return response.json();
      })
      .then(function (payload) {
        if (payload) {
          renderResponse(payload);
        }
      })
      .catch(function () {
        renderError("network");
      })
      .finally(function () {
        submitButton.disabled = false;
      });
  });
})();
