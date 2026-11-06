/* Translate interface labels only; JSON bodies and editors stay untouched. */
(() => {
  "use strict";
  const labels = new Map(Object.entries({
    "Try it out": "Спробувати",
    "Execute": "Виконати",
    "Cancel": "Скасувати",
    "Clear": "Очистити",
    "Reset": "Скинути",
    "Parameters": "Параметри",
    "No parameters": "Без параметрів",
    "Responses": "Відповіді",
    "Response": "Відповідь",
    "Server response": "Відповідь сервера",
    "Response body": "Тіло відповіді",
    "Response headers": "Заголовки відповіді",
    "Request body": "Тіло запиту",
    "Request URL": "Адреса запиту",
    "Code": "Код",
    "Details": "Подробиці",
    "Description": "Опис",
    "Links": "Посилання",
    "No links": "Немає посилань",
    "Name": "Назва",
    "Required": "Обов’язково",
    "required": "обов’язково",
    "Example Value": "Приклад значення",
    "Example": "Приклад",
    "Examples": "Приклади",
    "Schema": "Схема",
    "Schemas": "Моделі даних",
    "Model": "Модель",
    "Models": "Моделі",
    "Successful Response": "Успішна відповідь",
    "Validation Error": "Помилка перевірки даних",
    "Media type": "Тип даних",
    "Response content type": "Тип даних відповіді",
    "Request content type": "Тип даних запиту",
    "Download": "Завантажити",
    "Undocumented": "Не описано у схемі",
    "Available values": "Доступні значення",
    "Default value": "Типове значення",
    "Controls `Accept` header.": "Визначає заголовок Accept.",
    "Controls Accept header.": "Визначає заголовок Accept.",
    "Collapse operation": "Згорнути операцію",
    "Expand operation": "Розгорнути операцію",
    "Copy to clipboard": "Скопіювати",
    "Copy path to clipboard": "Скопіювати адресу",
    "Expand all": "Розгорнути все",
    "Collapse all": "Згорнути все",
    "Loading...": "Завантаження…",
    "Loading": "Завантаження",
  }));
  const root = document.getElementById("swagger-ui");
  if (!root) return;
  document.documentElement.lang = "uk";
  const excluded = "pre, code, textarea, input, script, style, [contenteditable], .highlight-code, .microlight";

  function translate() {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement?.closest(excluded)) continue;
      const text = node.nodeValue;
      const replacement = labels.get(text.trim());
      if (replacement) {
        node.nodeValue = text.replace(text.trim(), replacement);
      }
    }
    for (const element of root.querySelectorAll("[title], [aria-label]")) {
      if (element.closest(excluded)) continue;
      for (const attribute of ["title", "aria-label"]) {
        const replacement = labels.get(element.getAttribute(attribute));
        if (replacement) element.setAttribute(attribute, replacement);
      }
    }
  }

  // Swagger renders controls again when operations open or requests complete.
  new MutationObserver(translate).observe(root, {
    subtree: true, childList: true, characterData: true,
  });
  translate();
})();
