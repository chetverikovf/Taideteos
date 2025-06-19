const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

// Общая функция для выполнения запросов
async function request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Добавляем токен, если он есть
    const token = localStorage.getItem('accessToken');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred.' }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        // Для запросов, которые не возвращают тело (например, 204 No Content)
        if (response.status === 204) {
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Функции для конкретных эндпоинтов
export const api = {
    register: (username, password) => {
        return request('/users/register', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
    },
    login: (username, password) => {
        // Логин использует form-data, поэтому обрабатывается немного иначе
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        return fetch(`${API_BASE_URL}/users/login/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        }).then(async response => {
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail);
            }
            return response.json();
        });
    },
    
    /**
     * Получает список графов с пагинацией.
     * @param {number} page - Номер страницы (начиная с 1).
     * @param {number} limit - Количество элементов на странице.
     * @returns {Promise<Array>} - Массив объектов графов.
     */
    getGraphs: (page = 1, limit = 10, sortBy = 'date_desc', searchQuery = '') => {
        const skip = (page - 1) * limit;
        let url = `/graphs/?skip=${skip}&limit=${limit}&sort_by=${sortBy}`;
        // Добавляем параметр поиска, только если он не пустой
        if (searchQuery) {
            url += `&search=${encodeURIComponent(searchQuery)}`;
        }
        return request(url);
    },

    /**
     * Создает новый граф. Требует аутентификации.
     * @param {string} name - Имя графа.
     * @param {string} description - Описание графа.
     * @returns {Promise<Object>} - Объект созданного графа.
     */
    createGraph: (name, description) => {
        return request('/graphs/', {
            method: 'POST',
            body: JSON.stringify({ name, description }),
        });
    },

    /**
     * Получает детальную информацию о графе, включая элементы для Cytoscape.
     * @param {string} graphId - UUID графа.
     * @returns {Promise<Object>} - Объект с деталями графа.
    */
    getGraphDetails: (graphId) => {
        return request(`/graphs/${graphId}`);
    },

    // Добавление узла и ребра 
    addNodeToGraph: (graphId, nodeData) => {
        return request(`/graphs/${graphId}/nodes`, {
            method: 'POST',
            body: JSON.stringify(nodeData),
        });
    },

    addEdgeToGraph: (graphId, edgeData) => {
        return request(`/graphs/${graphId}/edges`, {
            method: 'POST',
            body: JSON.stringify(edgeData),
        });
    },

    getNodeDetails: (nodeId) => {
        return request(`/nodes/${nodeId}`);
    },
    
    // Обновление и удаление
    updateNode: (nodeId, nodeData) => {
        return request(`/nodes/${nodeId}`, {
            method: 'PATCH',
            body: JSON.stringify(nodeData),
        });
    },

    // --- МЕТОДЫ  УЗЛОВ И ГРАНЕЙ ---
    deleteNode: (nodeId) => {
        return request(`/nodes/${nodeId}`, { method: 'DELETE' });
    },

    deleteEdge: (edgeId) => {
        return request(`/edges/${edgeId}`, { method: 'DELETE' });
    },

    // --- МЕТОДЫ  ПРОГРЕССА ---
    markNodeAsLearned: (nodeId) => {
        return request(`/nodes/${nodeId}/progress`, { method: 'POST' });
    },
    unmarkNodeAsLearned: (nodeId) => {
        return request(`/nodes/${nodeId}/progress`, { method: 'DELETE' });
    },

    // --- МЕТОДЫ ПРОФИЛЯ  ---
    getProfile: () => {
        return request('/users/me/profile');
    },

    rateGraph: (graphId, value) => {
        // value должно быть 1 или -1
        return request(`/graphs/${graphId}/rate`, {
            method: 'POST',
            body: JSON.stringify({ value }),
        });
    },

    // --- МЕТОДЫ КОММЕНТАРИЕВ  ---
    getComments: (graphId, page = 1, limit = 10) => {
        const skip = (page - 1) * limit;
        return request(`/graphs/${graphId}/comments?skip=${skip}&limit=${limit}`);
    },
    
    addComment: (graphId, content) => {
        return request(`/graphs/${graphId}/comments`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        });
    },

};

