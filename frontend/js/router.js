import { api } from './api.js';
import { login, logout, isLoggedIn } from './auth.js';

// Контейнер, куда будут загружаться страницы
const appRoot = document.getElementById('app-root');
const navAuthLinks = document.getElementById('nav-auth-links');
let currentCommentsPage = 1;
const COMMENTS_PER_PAGE = 5;
const GRAPHS_PER_PAGE = 10;

// Карта маршрутов
const routes = [
    { path: /^\/$/, view: '/pages/home.html' },
    { path: /^\/login$/, view: '/pages/login.html' },
    { path: /^\/register$/, view: '/pages/register.html' },
    { path: /^\/graphs$/, view: '/pages/graphs.html' },
    { path: /^\/graphs\/create$/, view: '/pages/create_graph.html' },
    { path: /^\/graphs\/([0-9a-fA-F-]+)\/edit$/, view: '/pages/edit_graph.html' },
    { path: /^\/graphs\/([0-9a-fA-F-]+)$/, view: '/pages/view_graph.html' },
    { path: /^\/nodes\/([0-9a-fA-F-]+)\/edit$/, view: '/pages/edit_node.html' },
    { path: /^\/nodes\/([0-9a-fA-F-]+)$/, view: '/pages/view_node.html' },
    { path: /^\/profile$/, view: '/pages/profile.html' },
];

// Функция для навигации
export async function navigateTo(path) {
    const [pathname] = path.split('?');
    const privateRouteRules = [ '/graphs/create', '/profile', /^\/graphs\/.*\/edit$/, /^\/nodes\/.*\/edit$/ ];
    const isPathPrivate = privateRouteRules.some(rule => (typeof rule === 'string') ? pathname === rule : rule.test(pathname));

    if (isPathPrivate && !isLoggedIn()) {
        navigateTo('/login');
        return;
    }

    const potentialMatch = routes.find(route => route.path.test(pathname));
    const match = potentialMatch || { view: '/pages/not_found.html' };
    
    try {
        const view = await fetch(match.view).then(res => {
            if (!res.ok) throw new Error(`Не удалось загрузить шаблон: ${res.statusText}`);
            return res.text();
        });
        appRoot.innerHTML = view;
        window.history.pushState({}, '', path);
        afterPageLoad(pathname, potentialMatch ? pathname.match(potentialMatch.path) : null);
    } catch(error) {
        console.error("Ошибка при навигации:", error);
        appRoot.innerHTML = `<div class="alert alert-danger">Ошибка: Не удалось загрузить страницу.</div>`;
    }
}

// Функция, которая будет вызываться после загрузки каждой страницы

function afterPageLoad(path, match) {
    if (path === '/profile') { renderProfilePage(); }
    else if (path === '/login') { const form = document.getElementById('login-form'); if (form) form.addEventListener('submit', handleLogin); } 
    else if (path === '/register') { const form = document.getElementById('register-form'); if (form) form.addEventListener('submit', handleRegister); }
    else if (path === '/graphs') { renderGraphsList(); } 
    else if (path === '/graphs/create') { const form = document.getElementById('create-graph-form'); if (form) form.addEventListener('submit', handleCreateGraph); }
    else if (match && path.startsWith('/graphs/') && path.endsWith('/edit')) { renderGraphEditor(match[1]); }
    else if (match && path.startsWith('/nodes/') && path.endsWith('/edit')) { renderNodeEditor(match[1]); }
    else if (match && path.startsWith('/nodes/')) { renderNodeView(match[1]); }
    else if (match && path.startsWith('/graphs/')) { renderGraphView(match[1]); }
}

// --- ФУНКЦИЯ для редактора графа ---
async function renderGraphEditor(graphId) {
    try {
        const graphData = await api.getGraphDetails(graphId);
        
        document.getElementById('graph-name').textContent = `Редактирование: ${graphData.name}`;
        document.getElementById('view-graph-link').href = `/graphs/${graphId}`;

        const cy = cytoscape({
            container: document.getElementById('cy-edit'),
            elements: graphData.elements,
            style: [ { selector: 'node', style: { 'background-color': '#0d6efd', 'label': 'data(label)', 'color': '#fff', 'text-outline-color': '#0d6efd', 'text-outline-width': 2, 'font-size': '16px' } }, { selector: 'edge', style: { 'width': 3, 'line-color': '#adb5bd', 'target-arrow-shape': 'triangle', 'target-arrow-color': '#adb5bd', 'curve-style': 'bezier' } }, { selector: 'node:selected', style: { 'border-color': 'yellow', 'border-width': 3 } }, { selector: 'edge:selected', style: { 'line-color': 'yellow', 'target-arrow-color': 'yellow' } } ],
            layout: { name: 'preset' },
        });

        cy.style()
            .selector('node.edge-mode').style({ 'border-color': '#28a745', 'border-width': 4, 'border-style': 'dashed' })
            .selector('node.edge-source').style({ 'background-color': '#ffc107', 'border-color': '#e83e8c', 'border-width': 4, 'border-style': 'solid' })
            .update();

        // --- Логика навигации ---
        document.getElementById('zoom-in-btn').addEventListener('click', () => cy.zoom(cy.zoom() * 1.2));
        document.getElementById('zoom-out-btn').addEventListener('click', () => cy.zoom(cy.zoom() * 0.8));
        document.getElementById('fit-btn').addEventListener('click', () => cy.fit());
        cy.minZoom(0.1);
        cy.maxZoom(3.0);

        // --- Логика редактирования (перетаскивание) ---
        cy.on('dragfreeon', 'node', async (e) => {
            const node = e.target;
            try {
                await api.updateNode(node.id(), { position_x: node.position().x, position_y: node.position().y });
            } catch (error) {
                console.error("Ошибка обновления позиции:", error);
                // Можно добавить уведомление для пользователя
            }
        });

        // --- Логика добавления узла (через модальное окно) ---
        const addNodeModal = new bootstrap.Modal(document.getElementById('addNodeModal'));
        document.getElementById('add-node-btn').addEventListener('click', () => {
            document.getElementById('add-node-modal-form').reset();
            addNodeModal.show();
        });
        document.getElementById('save-node-btn').addEventListener('click', async () => {
            const nodeName = document.getElementById('new-node-name').value.trim();
            if (!nodeName) return;
            const pan = cy.pan(); const zoom = cy.zoom();
            const pos = { x: -pan.x / zoom + cy.width() / (2 * zoom), y: -pan.y / zoom + cy.height() / (2 * zoom) };
            try {
                const newNodeData = await api.addNodeToGraph(graphId, { name: nodeName, position_x: pos.x, position_y: pos.y });
                cy.add({ group: 'nodes', data: { id: newNodeData.id, label: newNodeData.name }, position: pos });
                addNodeModal.hide();
            } catch (error) {
                alert(`Ошибка добавления узла: ${error.message}`);
            }
        });

        // --- Логика добавления связи (интерактивный режим) ---
        let edgeSourceNode = null;
        const addEdgeBtn = document.getElementById('add-edge-btn');
        const instructionsEl = document.getElementById('editor-instructions');
        const cyContainer = document.getElementById('cy-edit');

        function updateInstructions(text) {
            instructionsEl.style.display = text ? 'block' : 'none';
            instructionsEl.textContent = text;
        }

        function toggleEdgeMode(isActive) {
            if (isActive) {
                edgeSourceNode = null;
                addEdgeBtn.textContent = 'Отмена';
                addEdgeBtn.classList.add('btn-danger');
                addEdgeBtn.classList.remove('btn-outline-secondary');
                cy.nodes().addClass('edge-mode');
                cyContainer.style.cursor = 'pointer';
                updateInstructions('Шаг 1: Кликните на узел-ИСТОЧНИК.');
            } else {
                if (edgeSourceNode) edgeSourceNode.removeClass('edge-source');
                edgeSourceNode = null;
                addEdgeBtn.textContent = 'Добавить связь';
                addEdgeBtn.classList.remove('btn-danger');
                addEdgeBtn.classList.add('btn-outline-secondary');
                cy.nodes().removeClass('edge-mode');
                cyContainer.style.cursor = 'default';
                updateInstructions(null);
            }
        }
        addEdgeBtn.addEventListener('click', () => toggleEdgeMode(addEdgeBtn.textContent !== 'Отмена'));

        // --- Единый обработчик кликов ---
        const nodeActionModal = new bootstrap.Modal(document.getElementById('nodeActionModal'));
        
        cy.on('tap', (event) => {
            const target = event.target;
            const isInEdgeMode = addEdgeBtn.textContent === 'Отмена';

            if (isInEdgeMode) {
                // --- Логика для режима добавления ребра ---
                if (target.isNode && target.isNode()) {
                    if (!edgeSourceNode) {
                        edgeSourceNode = target;
                        edgeSourceNode.removeClass('edge-mode').addClass('edge-source');
                        updateInstructions('Шаг 2: Кликните на узел-ЦЕЛЬ.');
                    } else {
                        if (edgeSourceNode.id() !== target.id()) {
                            api.addEdgeToGraph(graphId, { source_node_id: edgeSourceNode.id(), target_node_id: target.id() })
                               .then(newEdge => cy.add({ group: 'edges', data: { ...newEdge, source: newEdge.source_node_id, target: newEdge.target_node_id } }))
                               .catch(err => alert(`Ошибка: ${err.message}`))
                               .finally(() => toggleEdgeMode(false));
                        } else {
                            toggleEdgeMode(false); // Кликнули на тот же узел, отмена
                        }
                    }
                } else if (target === cy) { // Клик по фону для отмены
                    toggleEdgeMode(false);
                }
            } else {
                // --- Логика для обычного режима ---
                if (target.isNode && target.isNode()) {
                    const nodeId = target.id();
                    const nodeName = target.data('label');
                    const nodeActionModalTitle = document.getElementById('nodeActionModalTitle');
                    const editNodeContentBtn = document.getElementById('edit-node-content-btn');
                    const deleteNodeBtn = document.getElementById('delete-node-btn');
                    
                    nodeActionModalTitle.textContent = `Узел: "${nodeName}"`;
                    
                    editNodeContentBtn.onclick = () => {
                        navigateTo(`/nodes/${nodeId}/edit?graph_id=${graphId}`);
                        nodeActionModal.hide();
                    };
                    deleteNodeBtn.onclick = () => {
                        if (confirm(`Вы уверены, что хотите удалить узел "${nodeName}"?`)) {
                            api.deleteNode(nodeId)
                               .then(() => cy.remove(target))
                               .catch(err => alert(`Ошибка удаления: ${err.message}`));
                        }
                        nodeActionModal.hide();
                    };
                    nodeActionModal.show();

                } else if (target.isEdge && target.isEdge()) {
                    if (confirm('Удалить эту связь?')) {
                        api.deleteEdge(target.id()).then(() => cy.remove(target));
                    }
                }
            }
        });

    } catch (error) {
        appRoot.innerHTML = `<p class="text-danger">Не удалось загрузить редактор: ${error.message}</p>`;
    }
}

// --- ФУНКЦИЯ для отрисовки графа ---
async function renderGraphView(graphId) {
    const infoContainer = document.getElementById('graph-info-container');
    if (infoContainer) { infoContainer.innerHTML = '<h1>Загрузка...</h1>'; } else { return; }

    try {
        const graphData = await api.getGraphDetails(graphId);
        
        const currentUserId = localStorage.getItem('userId');
        const isOwner = currentUserId && currentUserId === graphData.owner.id;
        let myVote = graphData.my_vote;

        const editButtonHtml = isOwner ? `<a href="/graphs/${graphId}/edit" class="btn btn-secondary" data-link>Редактировать граф</a>` : '';
        const ratingButtonsHtml = isLoggedIn() ? `
            <div class="ms-4" id="rating-controls">
                <button class="btn btn-sm ${myVote === 1 ? 'btn-primary' : 'btn-outline-secondary'}" data-vote="1" ${isOwner ? 'disabled' : ''}> ▲ <span class="like-count">${graphData.likes}</span> </button>
                <button class="btn btn-sm ${myVote === -1 ? 'btn-danger' : 'btn-outline-secondary'}" data-vote="-1" ${isOwner ? 'disabled' : ''}> ▼ <span class="dislike-count">${graphData.dislikes}</span> </button>
            </div>
        ` : '';

        infoContainer.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div><h1 id="graph-name">${escapeHtml(graphData.name)}</h1><p class="lead" id="graph-description">${escapeHtml(graphData.description || '')}</p></div>
                ${editButtonHtml}
            </div>
            <div class="d-flex align-items-center"><p class="text-muted mb-0" id="graph-meta">Создан: ${new Date(graphData.created_at).toLocaleDateString()} | Автор: ${escapeHtml(graphData.owner.username)}</p>${ratingButtonsHtml}</div>
        `;

        const ratingContainer = document.getElementById('rating-controls');
        if (ratingContainer) {
            ratingContainer.addEventListener('click', async (e) => {
                const button = e.target.closest('button[data-vote]');
                if (!button) return;
                button.disabled = true;
                const value = parseInt(button.dataset.vote, 10);
                try {
                    await api.rateGraph(graphId, value);
                    const likeBtn = ratingContainer.querySelector('[data-vote="1"]'), dislikeBtn = ratingContainer.querySelector('[data-vote="-1"]');
                    const likeCountSpan = likeBtn.querySelector('.like-count'), dislikeCountSpan = dislikeBtn.querySelector('.dislike-count');
                    let likes = parseInt(likeCountSpan.textContent, 10), dislikes = parseInt(dislikeCountSpan.textContent, 10);
                    if (myVote === value) { value === 1 ? likes-- : dislikes--; myVote = 0; }
                    else { if (myVote === 1) likes--; if (myVote === -1) dislikes--; value === 1 ? likes++ : dislikes++; myVote = value; }
                    likeCountSpan.textContent = likes; dislikeCountSpan.textContent = dislikes;
                    likeBtn.className = `btn btn-sm ${myVote === 1 ? 'btn-primary' : 'btn-outline-secondary'}`;
                    dislikeBtn.className = `btn btn-sm ${myVote === -1 ? 'btn-danger' : 'btn-outline-secondary'}`;
                } catch (error) { alert(`Ошибка: ${error.message}`); }
                finally { ratingContainer.querySelectorAll('button').forEach(btn => btn.disabled = false); }
            });
        }
        
        const learnedNodeIds = new Set(graphData.learned_node_ids || []);
        const cy = cytoscape({
            container: document.getElementById('cy'),
            elements: graphData.elements,
            style: [ { selector: 'node', style: { 'background-color': '#6c757d', 'label': 'data(label)', 'color': '#fff', 'text-outline-color': '#6c757d', 'text-outline-width': 2 } }, { selector: 'node.learned', style: { 'background-color': '#28a745', 'text-outline-color': '#28a745' } }, { selector: 'edge', style: { 'width': 3, 'line-color': '#adb5bd', 'target-arrow-color': '#adb5bd', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } }, ],
            layout: { name: 'preset', padding: 30 },
        });

        learnedNodeIds.forEach(nodeId => cy.getElementById(nodeId).addClass('learned'));
        document.getElementById('zoom-in-btn').addEventListener('click', () => cy.zoom(cy.zoom() * 1.2));
        document.getElementById('zoom-out-btn').addEventListener('click', () => cy.zoom(cy.zoom() * 0.8));
        document.getElementById('fit-btn').addEventListener('click', () => cy.fit());
        cy.minZoom(0.1); cy.maxZoom(3.0); cy.nodes().ungrabify();

        const nodeActionModal = new bootstrap.Modal(document.getElementById('viewNodeActionModal'));
        const modalTitle = document.getElementById('viewNodeActionModalTitle');
        const modalButtons = document.getElementById('viewNodeActionButtons');
        cy.on('tap', 'node', (event) => {
            const node = event.target, nodeId = node.id(), nodeName = node.data('label'), isLearned = node.hasClass('learned');
            modalTitle.textContent = `Узел: "${nodeName}"`;
            modalButtons.innerHTML = `<a href="/nodes/${nodeId}?graph_id=${graphId}" class="btn btn-primary" data-link>Перейти к контенту</a> ${isLoggedIn() ? `${isLearned ? `<button class="btn btn-warning" data-action="unmark">Снять отметку</button>` : `<button class="btn btn-success" data-action="mark">Отметить как изученное</button>`}` : ''}`;
            const markBtn = modalButtons.querySelector('[data-action="mark"]');
            if (markBtn) { markBtn.onclick = async () => { markBtn.disabled = true; try { await api.markNodeAsLearned(nodeId); node.addClass('learned'); nodeActionModal.hide(); } catch (error) { alert("Не удалось отметить узел."); markBtn.disabled = false; } }; }
            const unmarkBtn = modalButtons.querySelector('[data-action="unmark"]');
            if (unmarkBtn) { unmarkBtn.onclick = async () => { unmarkBtn.disabled = true; try { await api.unmarkNodeAsLearned(nodeId); node.removeClass('learned'); nodeActionModal.hide(); } catch (error) { alert("Не удалось убрать отметку."); unmarkBtn.disabled = false; } }; }
            const viewContentLink = modalButtons.querySelector('a[data-link]');
            if (viewContentLink) { viewContentLink.addEventListener('click', (e) => { e.preventDefault(); nodeActionModal.hide(); setTimeout(() => navigateTo(e.target.getAttribute('href')), 200); }); }
            nodeActionModal.show();
        });
        
        // --- Инициализируем комментарии ---
        initializeComments(graphId);

    } catch (error) {
        if(infoContainer) infoContainer.innerHTML = `<div class="alert alert-danger">Не удалось загрузить граф: ${escapeHtml(error.message)}</div>`;
    }
}

function initializeComments(graphId) {
    currentCommentsPage = 1; // Сбрасываем счетчик страниц
    const commentsList = document.getElementById('comments-list');
    const loadMoreContainer = document.getElementById('load-more-comments-container');
    const loadMoreBtn = document.getElementById('load-more-comments-btn');
    const addCommentContainer = document.getElementById('add-comment-form-container');
    const commentLoginPrompt = document.getElementById('comment-login-prompt');
    const addCommentForm = document.getElementById('add-comment-form');

    if (!commentsList || !loadMoreContainer || !addCommentContainer || !commentLoginPrompt || !addCommentForm) {
        console.error("Один или несколько элементов для комментариев не найдены.");
        return;
    }

    if (isLoggedIn()) {
        addCommentContainer.style.display = 'block';
        commentLoginPrompt.style.display = 'none';
    } else {
        addCommentContainer.style.display = 'none';
        commentLoginPrompt.style.display = 'block';
    }

    const renderComment = (comment) => {
        const el = document.createElement('div');
        el.className = 'card mb-3';
        el.innerHTML = `
            <div class="card-body"><p class="card-text">${escapeHtml(comment.content)}</p></div>
            <div class="card-footer text-muted"><strong>${escapeHtml(comment.owner.username)}</strong> <small> - ${new Date(comment.created_at).toLocaleString()}</small></div>
        `;
        return el;
    };

    const loadComments = async () => {
        loadMoreBtn.disabled = true;
        loadMoreBtn.textContent = 'Загрузка...';
        try {
            const comments = await api.getComments(graphId, currentCommentsPage, COMMENTS_PER_PAGE);
            if (currentCommentsPage === 1) commentsList.innerHTML = '';
            if (comments.length > 0) {
                comments.forEach(c => commentsList.appendChild(renderComment(c)));
                currentCommentsPage++;
            }
            loadMoreContainer.style.display = (comments.length < COMMENTS_PER_PAGE) ? 'none' : 'block';
        } catch (err) {
            commentsList.innerHTML = '<p class="text-danger">Не удалось загрузить комментарии.</p>';
        } finally {
            loadMoreBtn.disabled = false;
            loadMoreBtn.textContent = 'Загрузить еще';
        }
    };

    loadComments(); // Загружаем первую порцию
    loadMoreBtn.onclick = loadComments; // Используем onclick для простоты, т.к. кнопка одна

    addCommentForm.onsubmit = async (e) => { // Используем onsubmit
        e.preventDefault();
        const contentTextarea = document.getElementById('comment-content');
        const content = contentTextarea.value.trim();
        if (content) {
            try {
                const newComment = await api.addComment(graphId, content);
                commentsList.prepend(renderComment(newComment));
                contentTextarea.value = '';
            } catch (error) {
                alert(`Не удалось добавить комментарий: ${error.message}`);
            }
        }
    };
}

function renderPagination(totalItems, currentPage, otherParams = {}) {
    const paginationContainer = document.getElementById('pagination-controls');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(totalItems / GRAPHS_PER_PAGE);
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    paginationContainer.replaceWith(paginationContainer.cloneNode(true));
    const newPaginationContainer = document.getElementById('pagination-controls');

    let paginationHtml = '<ul class="pagination">';
    paginationHtml += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage - 1}">«</a></li>`;
    for (let i = 1; i <= totalPages; i++) {
        paginationHtml += `<li class="page-item ${i === currentPage ? 'active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
    }
    paginationHtml += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage + 1}">»</a></li>`;
    paginationHtml += '</ul>';
    newPaginationContainer.innerHTML = paginationHtml;

    newPaginationContainer.addEventListener('click', (e) => {
        e.preventDefault();
        const target = e.target;
        if (target.tagName === 'A' && !target.closest('.page-item').classList.contains('disabled')) {
            const page = parseInt(target.dataset.page, 10);
            renderGraphsList(page); // Вызываем renderGraphsList с новой страницей и старыми параметрами
        }
    });
}

// Отображение списка графов
async function renderGraphsList(page = 1) {
    const listContainer = document.getElementById('graphs-list');
    const paginationContainer = document.getElementById('pagination-controls');
    
    // Получаем текущие значения фильтров со страницы.
    // Если элементы еще не существуют, используем значения по умолчанию.
    const sortBySelect = document.getElementById('sort-by-select');
    const searchInput = document.getElementById('search-input');
    const sortBy = sortBySelect ? sortBySelect.value : 'date_desc';
    
    let searchQuery = searchInput ? searchInput.value.trim() : '';

    // Проверяем длину поискового запроса.
    // Если он есть, но слишком короткий, мы его не отправляем.
    // (Но позволяем отправлять пустой запрос для сброса поиска)
    if (searchQuery.length > 0 && searchQuery.length < 3) {
        // Можно показать пользователю уведомление, что запрос слишком короткий
        console.warn("Поисковый запрос слишком короткий. Минимум 3 символа.");
        // Обнуляем запрос, чтобы не отправлять его на сервер
        searchQuery = ''; 
    }

    // Устанавливаем заглушку на время загрузки
    if (listContainer) {
        listContainer.innerHTML = '<p>Загрузка...</p>';
    } else { 
        console.error("Контейнер #graphs-list не найден.");
        return; 
    }
    if (paginationContainer) paginationContainer.innerHTML = '';

    try {
        // Вызываем API со всеми параметрами
        const paginatedData = await api.getGraphs(page, GRAPHS_PER_PAGE, sortBy, searchQuery);
        const { total, graphs } = paginatedData;
        
        if (graphs.length === 0) {
            listContainer.innerHTML = (page === 1 && !searchQuery)
                ? '<p>Пока не создано ни одного графа. Будьте первым!</p>' 
                : '<p>Ничего не найдено. Попробуйте изменить фильтры.</p>';
        } else {
            const graphsHtml = graphs.map(graph => `
                <div class="col-md-6 mb-4">
                    <div class="card border-primary h-100">
                        <div class="card-body d-flex flex-column">
                            <h5 class="card-title">${escapeHtml(graph.name)}</h5>
                            <h6 class="card-subtitle mb-2 text-muted">by ${escapeHtml(graph.owner.username)}</h6>
                            <p class="card-text flex-grow-1">${escapeHtml(truncateText(graph.description, 120)) || 'Нет описания.'}</p>
                            <a href="/graphs/${graph.id}" data-link class="card-link mt-auto">Смотреть граф</a>
                        </div>
                        <div class="card-footer text-muted d-flex justify-content-between align-items-center">
                            <span>${new Date(graph.created_at).toLocaleDateString()}</span>
                            <div class="d-flex gap-2">
                                <span class="badge bg-primary-soft text-primary">▲ ${graph.likes}</span>
                                <span class="badge bg-danger-soft text-danger">▼ ${graph.dislikes}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
            listContainer.innerHTML = graphsHtml;
        }

        renderPagination(total, page);

        // --- Навешиваем обработчики на форму фильтров ---
        const filterForm = document.getElementById('filter-form');
        if(filterForm) {
            // Устанавливаем текущие значения в поля (важно для перезагрузки)
            document.getElementById('sort-by-select').value = sortBy;
            document.getElementById('search-input').value = searchQuery;

            // Обработчик для отправки формы (по нажатию Enter в поле поиска)
            filterForm.onsubmit = (e) => {
                e.preventDefault();
                renderGraphsList(1); // Новый поиск всегда с первой страницы
            };
            
            // Обработчик для смены сортировки
            document.getElementById('sort-by-select').onchange = () => {
                renderGraphsList(1);
            };
        }

    } catch (error) {
        listContainer.innerHTML = `<div class="alert alert-danger">Не удалось загрузить графы: ${error.message}</div>`;
    }
}

// Обработчик создания графа
async function handleCreateGraph(event) {
    event.preventDefault();
    const form = event.target;
    const name = form['graph-name'].value;
    const description = form['graph-description'].value;
    const errorDiv = document.getElementById('error-message');

    try {
        const newGraph = await api.createGraph(name, description);
        // Пока что просто перенаправляем в каталог
        // В будущем будет /graphs/${newGraph.id}/edit
        navigateTo(`/graphs/${newGraph.id}/edit`); 
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

// Вспомогательная функция для защиты от XSS
/**
 * Безопасно экранирует HTML-строку, используя возможности DOM.
 * @param {string} unsafe - Строка для экранирования.
 * @returns {string} - Безопасная строка.
 */
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(unsafe));
    return div.innerHTML;
}

/**
 * Обрезает строку до заданной длины и добавляет многоточие.
 * @param {string} text - Исходный текст.
 * @param {number} maxLength - Максимальная длина.
 * @returns {string} - Обрезанный текст.
 */
function truncateText(text, maxLength = 120) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Обработчик для формы входа
async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const username = form.username.value;
    const password = form.password.value;
    const errorDiv = document.getElementById('error-message');

    try {
        const data = await api.login(username, password);
        login(data.access_token);
        navigateTo('/'); // Перенаправляем на главную после успеха
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

// Обработчик для формы регистрации
async function handleRegister(event) {
    event.preventDefault();
    const form = event.target;
    const username = form.username.value;
    const password = form.password.value;
    const errorDiv = document.getElementById('error-message');

    try {
        await api.register(username, password);
        // Автоматически логиним пользователя после успешной регистрации
        const data = await api.login(username, password);
        login(data.access_token);
        navigateTo('/'); // Перенаправляем на главную
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

// Обновление навигационной панели
export function updateNav() {
    const createGraphLink = document.getElementById('nav-create-graph-link');
    if (isLoggedIn()) {
        navAuthLinks.innerHTML = `
            <li class="nav-item"><a class="nav-link" href="/profile" data-link>Профиль</a></li>
            <li class="nav-item"><a class="nav-link" href="#" id="logout-link">Выйти</a></li>
        `;
        const logoutLink = document.getElementById('logout-link');
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                logout(); // Просто меняем состояние
                navigateTo('/'); // Явно переходим на главную
            });
        }
        if (createGraphLink) {
            createGraphLink.style.display = 'block';
        }
    } else {
        navAuthLinks.innerHTML = `
            <li class="nav-item"><a class="nav-link" href="/login" data-link>Войти</a></li>
            <li class="nav-item"><a class="nav-link" href="/register" data-link>Регистрация</a></li>
        `;
        if (createGraphLink) {
            createGraphLink.style.display = 'none';
        }
    }
}

// --- ФУНКЦИЯ для редактора узла ---
async function renderNodeEditor(nodeId) {
    try {
        const nodeData = await api.getNodeDetails(nodeId);
        
        document.getElementById('node-name-header').textContent = `Редактирование узла: "${nodeData.name}"`;
        
        const backLink = document.getElementById('back-to-graph-link');
        const urlParams = new URLSearchParams(window.location.search);
        const graphId = urlParams.get('graph_id');
        
        if (graphId) {
            backLink.href = `/graphs/${graphId}/edit`;
        } else {
            backLink.href = `/graphs`;
            backLink.textContent = '← Вернуться к каталогу';
        }

        const editor = document.getElementById('node-content-editor');
        const preview = document.getElementById('node-content-preview');
        const saveBtn = document.getElementById('save-node-content-btn');
        const saveStatus = document.getElementById('save-status');
        
        editor.value = nodeData.content || '';

        const updatePreview = () => {
            try {
                if (window.marked && window.renderMathInElement) {
                    const html = marked.parse(editor.value);
                    preview.innerHTML = html;
                    renderMathInElement(preview, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                        ],
                        throwOnError: false
                    });
                }
            } catch (e) {
                preview.innerHTML = `<div class="alert alert-danger">Ошибка рендеринга: ${e.message}</div>`;
            }
        };

        editor.addEventListener('input', updatePreview);
        updatePreview();
        
        saveBtn.addEventListener('click', async () => {
            saveBtn.disabled = true;
            saveStatus.style.display = 'block';
            saveStatus.className = 'mt-2 text-info';
            saveStatus.textContent = 'Сохранение...';
            try {
                await api.updateNode(nodeId, { content: editor.value });
                saveStatus.textContent = 'Сохранено успешно!';
                saveStatus.className = 'mt-2 text-success';
            } catch (error) {
                saveStatus.textContent = `Ошибка сохранения: ${error.message}`;
                saveStatus.className = 'mt-2 text-danger';
            } finally {
                setTimeout(() => { 
                    saveBtn.disabled = false; 
                    saveStatus.style.display = 'none'; 
                }, 2000);
            }
        });

    } catch (error) {
        appRoot.innerHTML = `<p class="text-danger">Не удалось загрузить редактор узла: ${error.message}</p>`;
    }
}

// --- ФУНКЦИЯ ДЛЯ ПРОСМОТРА УЗЛА ---
async function renderNodeView(nodeId) {
    try {
        const nodeData = await api.getNodeDetails(nodeId);
        
        document.getElementById('node-view-name-header').textContent = nodeData.name;

        const backLink = document.getElementById('back-to-graph-view-link');
        const urlParams = new URLSearchParams(window.location.search);
        const graphId = urlParams.get('graph_id');
        
        if (graphId) {
            // Формируем правильную ссылку на просмотр графа
            backLink.href = `/graphs/${graphId}`;
        } else {
            backLink.href = '/graphs';
            backLink.textContent = '← Вернуться к каталогу';
        }

        const preview = document.getElementById('node-view-content');
        
        // Рендерим контент
        if (nodeData.content) {
            const html = marked.parse(nodeData.content);
            preview.innerHTML = html;
            // Просим KaTeX найти и отрендерить формулы
            renderMathInElement(preview, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                ],
                throwOnError: false
            });
        } else {
            preview.innerHTML = '<p class="text-muted">Содержимое для этого узла еще не добавлено.</p>';
        }

    } catch (error) {
        appRoot.innerHTML = `<p class="text-danger">Не удалось загрузить данные узла: ${error.message}</p>`;
    }
}

async function renderProfilePage() {
    const loader = document.getElementById('profile-loader');
    const content = document.getElementById('profile-content');

    try {
        const profileData = await api.getProfile();

        // Заполняем основные данные
        document.getElementById('profile-username').textContent = profileData.username;
        document.getElementById('profile-likes').textContent = `▲ ${profileData.total_likes}`;
        document.getElementById('profile-dislikes').textContent = `▼ ${profileData.total_dislikes}`;

        // Заполняем список созданных графов
        const ownedList = document.getElementById('owned-graphs-list');
        if (profileData.owned_graphs.length > 0) {
            ownedList.innerHTML = profileData.owned_graphs.map(graph => `
                <a href="/graphs/${graph.id}/edit" class="list-group-item list-group-item-action" data-link>
                    <strong>${escapeHtml(graph.name)}</strong>
                    <small class="d-block text-muted">Создан: ${new Date(graph.created_at).toLocaleDateString()}</small>
                </a>
            `).join('');
        } else {
            ownedList.innerHTML = '<p class="text-muted">Вы еще не создали ни одного графа.</p>';
        }

        // Заполняем список изучаемых графов
        const learningList = document.getElementById('learning-graphs-list');
        if (profileData.learning_graphs.length > 0) {
            learningList.innerHTML = profileData.learning_graphs.map(graph => `
                <a href="/graphs/${graph.id}" class="list-group-item list-group-item-action" data-link>
                    <strong>${escapeHtml(graph.name)}</strong>
                    <small class="d-block text-muted">Автор: ${escapeHtml(graph.owner.username)}</small>
                </a>
            `).join('');
        } else {
            learningList.innerHTML = '<p class="text-muted">Вы еще не начали изучение ни одного графа.</p>';
        }

        // Показываем контент
        loader.style.display = 'none';
        content.style.display = 'block';

    } catch (error) {
        loader.innerHTML = `<div class="alert alert-danger">Не удалось загрузить профиль: ${error.message}</div>`;
    }
}