import { navigateTo, updateNav } from './router.js';

// Обрабатываем клики по ссылкам, чтобы избежать перезагрузки страницы
document.addEventListener('click', (e) => {
    if (e.target.matches('[data-link]')) {
        e.preventDefault();
        navigateTo(e.target.getAttribute('href'));
    }
});

// Обрабатываем навигацию кнопками "вперед/назад" в браузере
window.addEventListener('popstate', () => {
    navigateTo(window.location.pathname);
});

// Запускаем приложение при первой загрузке
document.addEventListener('DOMContentLoaded', () => {
    updateNav(); // Сразу обновляем навбар
    navigateTo(window.location.pathname); // Загружаем текущую страницу
});