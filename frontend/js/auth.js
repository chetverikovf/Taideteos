import { updateNav } from './router.js'; // Импортируем для обновления навбара

function parseJwt (token) {
    var base64Url = token.split('.')[1];
    var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    var jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    return JSON.parse(jsonPayload);
}

export function login(token) {
    localStorage.setItem('accessToken', token);
    try {
        const decoded = parseJwt(token);
        console.log(decoded)
        if (decoded.user_id) {
            localStorage.setItem('userId', decoded.user_id);
        }
    } catch (e) {
        console.error("Invalid token:", e);
    }
    updateNav();
}

export function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('userId');
    updateNav();
}

export function isLoggedIn() {
    return !!localStorage.getItem('accessToken');
}