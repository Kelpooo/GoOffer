const DOMAIN_DEFINITIONS = [
  { value: "frontend", label: "前端", desc: "HTML / CSS / JavaScript / React / Vue" },
  { value: "backend", label: "后端", desc: "MySQL / Redis / 并发 / 服务端" },
  { value: "ai_app", label: "AI 应用开发", desc: "RAG / Prompt / Agent / Workflow" },
  { value: "testing", label: "测试开发", desc: "接口测试 / 自动化 / 性能 / 质量体系" },
  { value: "algorithm", label: "算法工程师", desc: "机器学习 / 推荐 / NLP / 建模" },
  { value: "ops", label: "运维 / 云原生", desc: "Linux / Docker / Kubernetes / 监控" },
  { value: "cs_basic", label: "计算机基础", desc: "操作系统 / 网络 / 数据结构 / 数据库" },
];

const JOB_TRACKS = [
  { value: "all", label: "全部方向" },
  { value: "frontend", label: "前端" },
  { value: "backend", label: "后端" },
  { value: "ai_app", label: "AI 应用开发" },
  { value: "testing", label: "测试开发" },
  { value: "algorithm", label: "算法工程师" },
  { value: "ops", label: "运维 / 云原生" },
];

const state = {
  allQuestions: [],
  filteredQuestions: [],
  visitorStats: null,
  authMode: "login",
  currentUser: null,
  authPolicy: null,
  accountOverview: null,
  progressApiAvailable: false,
  practicedThisSession: new Set(),
  selectedDomain: "frontend",
  selectedCategory: "all",
  selectedDifficulty: "all",
  search: "",
  selectedQuestionId: null,
  currentView: "home",
  interviewQuestionId: null,
  interviewReveal: false,
  interviewAnswers: {},
  interviewAnswerSyncTimers: new Map(),
  interviewApiAvailable: false,
  jobsData: { companies: [], jobs: [] },
  jobSearch: "",
  selectedJobCompany: "all",
  selectedJobTrack: "all",
  resumeReview: null,
  resumeRewrite: null,
  resumeInterviewPack: null,
  favorites: loadSet("mvp_favorites"),
  mastered: loadSet("mvp_mastered"),
  practice: loadPracticeMap("mvp_practice"),
};

const elements = {
  mainNav: document.getElementById("mainNav"),
  authLoggedOut: document.getElementById("authLoggedOut"),
  authLoggedIn: document.getElementById("authLoggedIn"),
  authStatus: document.getElementById("authStatus"),
  authTabs: document.getElementById("authTabs"),
  showLoginTabBtn: document.getElementById("showLoginTabBtn"),
  showRegisterTabBtn: document.getElementById("showRegisterTabBtn"),
  loginForm: document.getElementById("loginForm"),
  loginUsername: document.getElementById("loginUsername"),
  loginPassword: document.getElementById("loginPassword"),
  registerForm: document.getElementById("registerForm"),
  registerUsername: document.getElementById("registerUsername"),
  registerPassword: document.getElementById("registerPassword"),
  registerConfirmPassword: document.getElementById("registerConfirmPassword"),
  currentUsername: document.getElementById("currentUsername"),
  logoutBtn: document.getElementById("logoutBtn"),
  accountBadge: document.getElementById("accountBadge"),
  accountUserBox: document.getElementById("accountUserBox"),
  accountStats: document.getElementById("accountStats"),
  accountStatus: document.getElementById("accountStatus"),
  practiceSummary: document.getElementById("practiceSummary"),
  accountRecords: document.getElementById("accountRecords"),
  changePasswordForm: document.getElementById("changePasswordForm"),
  currentPasswordInput: document.getElementById("currentPasswordInput"),
  newPasswordInput: document.getElementById("newPasswordInput"),
  confirmPasswordInput: document.getElementById("confirmPasswordInput"),
  changePasswordBtn: document.getElementById("changePasswordBtn"),
  domainSwitch: document.getElementById("domainSwitch"),
  heroStats: document.getElementById("heroStats"),
  homeDomainGrid: document.getElementById("homeDomainGrid"),
  browseTitle: document.getElementById("browseTitle"),
  searchInput: document.getElementById("searchInput"),
  difficultyFilter: document.getElementById("difficultyFilter"),
  categoryList: document.getElementById("categoryList"),
  questionList: document.getElementById("questionList"),
  questionDetail: document.getElementById("questionDetail"),
  resultCount: document.getElementById("resultCount"),
  favoriteCount: document.getElementById("favoriteCount"),
  masteredCount: document.getElementById("masteredCount"),
  jumpToFavoritesBtn: document.getElementById("jumpToFavoritesBtn"),
  goBrowseBtn: document.getElementById("goBrowseBtn"),
  goInterviewBtn: document.getElementById("goInterviewBtn"),
  goResumeBtn: document.getElementById("goResumeBtn"),
  goReviewBtn: document.getElementById("goReviewBtn"),
  randomFromHomeBtn: document.getElementById("randomFromHomeBtn"),
  homeSearchInput: document.getElementById("homeSearchInput"),
  homeAuthBtn: document.getElementById("homeAuthBtn"),
  heroStartBtn: document.getElementById("heroStartBtn"),
  heroPlanBtn: document.getElementById("heroPlanBtn"),
  homeFeaturedTabs: document.getElementById("homeFeaturedTabs"),
  homeFeaturedList: document.getElementById("homeFeaturedList"),
  homeAccountBox: document.getElementById("homeAccountBox"),
  homeRecordList: document.getElementById("homeRecordList"),
  randomQuestionBtn: document.getElementById("randomQuestionBtn"),
  jobSearchInput: document.getElementById("jobSearchInput"),
  jobsMeta: document.getElementById("jobsMeta"),
  jobsTrackFilters: document.getElementById("jobsTrackFilters"),
  jobsCompanyGrid: document.getElementById("jobsCompanyGrid"),
  jobsList: document.getElementById("jobsList"),
  favoritesList: document.getElementById("favoritesList"),
  masteredList: document.getElementById("masteredList"),
  favoritesLabel: document.getElementById("favoritesLabel"),
  masteredLabel: document.getElementById("masteredLabel"),
  refreshInterviewBtn: document.getElementById("refreshInterviewBtn"),
  interviewMeta: document.getElementById("interviewMeta"),
  interviewQuestion: document.getElementById("interviewQuestion"),
  interviewDraft: document.getElementById("interviewDraft"),
  interviewSubmitBtn: document.getElementById("interviewSubmitBtn"),
  toggleInterviewAnswerBtn: document.getElementById("toggleInterviewAnswerBtn"),
  markInterviewFavoriteBtn: document.getElementById("markInterviewFavoriteBtn"),
  markInterviewMasteredBtn: document.getElementById("markInterviewMasteredBtn"),
  interviewReveal: document.getElementById("interviewReveal"),
  interviewAnswerPoints: document.getElementById("interviewAnswerPoints"),
  interviewFollowUps: document.getElementById("interviewFollowUps"),
  interviewAnswerStatus: document.getElementById("interviewAnswerStatus"),
  resumeForm: document.getElementById("resumeForm"),
  resumeFile: document.getElementById("resumeFile"),
  resumeRole: document.getElementById("resumeRole"),
  resumeStack: document.getElementById("resumeStack"),
  resumeJd: document.getElementById("resumeJd"),
  resumeStatus: document.getElementById("resumeStatus"),
  resumeResult: document.getElementById("resumeResult"),
  resumeSubmitBtn: document.getElementById("resumeSubmitBtn"),
  resumeFollowupActions: document.getElementById("resumeFollowupActions"),
  generateRewriteBtn: document.getElementById("generateRewriteBtn"),
  generateInterviewPackBtn: document.getElementById("generateInterviewPackBtn"),
  resumeGenerated: document.getElementById("resumeGenerated"),
  views: {
    home: document.getElementById("homeView"),
    browse: document.getElementById("browseView"),
    detail: document.getElementById("detailView"),
    interview: document.getElementById("interviewView"),
    resume: document.getElementById("resumeView"),
    jobs: document.getElementById("jobsView"),
    review: document.getElementById("reviewView"),
    account: document.getElementById("accountView"),
  },
};

bootstrap();

async function bootstrap() {
  const [questionsPayload, jobsResponse, visitorStats, userProgress, authState, interviewAnswers] = await Promise.all([
    loadQuestionsPayload(),
    fetch("./data/jobs.json"),
    fetch("/api/site-stats")
      .then((response) => response.json())
      .catch(() => ({ ok: false })),
    loadUserProgress(),
    loadAuthState(),
    loadInterviewAnswers(),
  ]);

  const jobsPayload = await jobsResponse.json();

  state.allQuestions = questionsPayload.questions || [];
  state.jobsData = jobsPayload || { companies: [], jobs: [] };
  state.visitorStats = visitorStats?.ok ? visitorStats : null;
  applyAuthState(authState);
  applyUserProgress(userProgress);
  applyInterviewAnswers(interviewAnswers);
  if (state.currentUser) {
    await loadAccountOverview().catch(() => null);
  }

  bindEvents();
  render();
}

async function loadQuestionsPayload() {
  try {
    const apiResponse = await fetch("/api/questions");
    if (apiResponse.ok) {
      return await apiResponse.json();
    }
  } catch (error) {
    console.warn("Failed to load questions from API, falling back to static JSON.", error);
  }

  const staticResponse = await fetch("./data/questions.json");
  return staticResponse.json();
}

async function loadUserProgress() {
  try {
    const response = await fetch("/api/user-progress");
    if (!response.ok) throw new Error("progress api unavailable");
    return await response.json();
  } catch (error) {
    console.warn("Failed to load user progress from API, falling back to localStorage only.", error);
    return null;
  }
}

async function loadAuthState() {
  try {
    const response = await fetch("/api/auth/me");
    if (!response.ok) throw new Error("auth api unavailable");
    return await response.json();
  } catch (error) {
    console.warn("Failed to load auth state.", error);
    return null;
  }
}

async function loadInterviewAnswers() {
  try {
    const response = await fetch("/api/interview-answers");
    if (!response.ok) throw new Error("interview answers api unavailable");
    return await response.json();
  } catch (error) {
    console.warn("Failed to load interview answers from API, falling back to localStorage only.", error);
    return null;
  }
}

function applyAuthState(payload) {
  const nextUserId = payload?.authenticated ? payload.user?.id || payload.user?.username || "" : "";
  const currentUserId = state.currentUser?.id || state.currentUser?.username || "";
  state.currentUser = payload?.authenticated ? payload.user : null;
  state.authPolicy = payload?.policy || null;
  if (nextUserId !== currentUserId) {
    state.practicedThisSession.clear();
    clearInterviewAnswerTimers();
    state.interviewAnswers = {};
  }
}

function applyUserProgress(payload) {
  const localFavorites = loadSet("mvp_favorites");
  const localMastered = loadSet("mvp_mastered");
  const localPractice = loadPracticeMap("mvp_practice");

  if (!payload?.ok) {
    state.favorites = localFavorites;
    state.mastered = localMastered;
    state.practice = localPractice;
    state.progressApiAvailable = false;
    return;
  }

  state.progressApiAvailable = true;
  const serverPractice = normalizePracticeMap(payload.practice || {});

  const mergedFavorites = new Set([...(payload.favorites || []), ...localFavorites]);
  const mergedMastered = new Set([...(payload.mastered || []), ...localMastered]);
  const mergedPractice = mergePracticeMaps(serverPractice, localPractice);

  state.favorites = mergedFavorites;
  state.mastered = mergedMastered;
  state.practice = mergedPractice;
  persistLocalSet("mvp_favorites", state.favorites);
  persistLocalSet("mvp_mastered", state.mastered);
  persistPracticeMap("mvp_practice", state.practice);

  const needsSync =
    mergedFavorites.size !== (payload.favorites || []).length ||
    mergedMastered.size !== (payload.mastered || []).length;
  if (needsSync) {
    syncProgressToServer().catch((error) => console.warn("Failed to sync merged local progress.", error));
  }

  if (state.currentUser && hasPracticeDeficit(mergedPractice, serverPractice)) {
    syncPracticeToServer(mergedPractice, serverPractice)
      .then(() => loadAccountOverview().catch((error) => console.warn("Failed to refresh account overview after practice sync.", error)))
      .catch((error) => console.warn("Failed to sync local practice records.", error));
  }
}

function applyInterviewAnswers(payload) {
  const localAnswers = loadInterviewAnswersLocalMap();
  if (!payload?.ok) {
    state.interviewApiAvailable = false;
    state.interviewAnswers = localAnswers;
    persistInterviewAnswersLocalMap(state.interviewAnswers);
    return;
  }

  state.interviewApiAvailable = true;
  const serverAnswers = normalizeInterviewAnswerMap(payload.interviewAnswers || {});
  const mergedAnswers = mergeInterviewAnswerMaps(serverAnswers, localAnswers);

  state.interviewAnswers = mergedAnswers;
  persistInterviewAnswersLocalMap(state.interviewAnswers);

  if (hasInterviewAnswerDeficit(mergedAnswers, serverAnswers)) {
    syncInterviewAnswersToServer(mergedAnswers).catch((error) => console.warn("Failed to sync interview answers.", error));
  }
}

function bindEvents() {
  elements.homeSearchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
  });
  elements.homeSearchInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    performHomeSearch(elements.homeSearchInput.value.trim());
  });
  elements.homeAuthBtn.addEventListener("click", () => navigate("account"));
  elements.heroStartBtn.addEventListener("click", () => navigate("browse"));
  elements.heroPlanBtn.addEventListener("click", () => navigate("resume"));
  elements.showLoginTabBtn.addEventListener("click", () => switchAuthMode("login"));
  elements.showRegisterTabBtn.addEventListener("click", () => switchAuthMode("register"));
  elements.loginForm.addEventListener("submit", handleLoginSubmit);
  elements.registerForm.addEventListener("submit", handleRegisterSubmit);
  elements.logoutBtn.addEventListener("click", handleLogout);
  elements.changePasswordForm.addEventListener("submit", handleChangePassword);

  elements.mainNav.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => navigate(button.dataset.view));
  });

  elements.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderBrowse();
  });

  elements.difficultyFilter.addEventListener("change", (event) => {
    state.selectedDifficulty = event.target.value;
    renderBrowse();
  });

  elements.jobSearchInput.addEventListener("input", (event) => {
    state.jobSearch = event.target.value.trim().toLowerCase();
    renderJobs();
  });

  elements.jumpToFavoritesBtn.addEventListener("click", () => navigate("review"));
  elements.goBrowseBtn.addEventListener("click", () => navigate("browse"));
  elements.goInterviewBtn.addEventListener("click", () => {
    ensureInterviewQuestion();
    const question = findInterviewQuestion();
    if (question) markQuestionPracticed(question.id);
    navigate("interview");
  });
  elements.goResumeBtn.addEventListener("click", () => navigate("resume"));
  elements.goReviewBtn.addEventListener("click", () => navigate("review"));
  elements.randomFromHomeBtn.addEventListener("click", openRandomQuestion);
  elements.randomQuestionBtn.addEventListener("click", openRandomQuestion);

  elements.refreshInterviewBtn.addEventListener("click", () => {
    chooseRandomInterviewQuestion();
    const question = findInterviewQuestion();
    if (question) markQuestionPracticed(question.id);
    renderInterview();
  });

  elements.interviewDraft.addEventListener("input", () => {
    const question = findInterviewQuestion();
    if (!question) return;
    const record = updateInterviewAnswerCache(question.id, elements.interviewDraft.value);
    scheduleInterviewAnswerSync(question.id, record);
  });

  elements.interviewSubmitBtn.addEventListener("click", async () => {
    const question = findInterviewQuestion();
    if (!question) return;
    const answer = elements.interviewDraft.value.trim();
    if (!answer) {
      if (elements.interviewAnswerStatus) {
        elements.interviewAnswerStatus.textContent = "先写下你的回答，再提交。";
      }
      return;
    }
    const record = updateInterviewAnswerCache(question.id, answer);
    clearInterviewAnswerSyncTimer(question.id);
    try {
      await persistInterviewAnswerToServer(question.id, record.answer, record.updatedAt);
    } catch (error) {
      console.warn("Failed to persist interview answer.", error);
    }
    markQuestionPracticed(question.id);
    if (elements.interviewAnswerStatus) {
      elements.interviewAnswerStatus.textContent = "已提交你的回答。可以展开参考答案继续对照。";
    }
  });

  elements.toggleInterviewAnswerBtn.addEventListener("click", () => {
    state.interviewReveal = !state.interviewReveal;
    renderInterview();
  });

  elements.markInterviewFavoriteBtn.addEventListener("click", () => {
    const question = findInterviewQuestion();
    if (!question) return;
    updateQuestionStatus(question.id, { favorite: !state.favorites.has(question.id) });
  });

  elements.markInterviewMasteredBtn.addEventListener("click", () => {
    const question = findInterviewQuestion();
    if (!question) return;
    updateQuestionStatus(question.id, { mastered: !state.mastered.has(question.id) });
  });

  elements.resumeForm.addEventListener("submit", handleResumeReviewSubmit);
  elements.resumeSubmitBtn.addEventListener("click", handleResumeReviewSubmit);
  elements.generateRewriteBtn.addEventListener("click", handleResumeRewrite);
  elements.generateInterviewPackBtn.addEventListener("click", handleResumeInterviewPack);
}

function render() {
  renderAuthPanel();
  renderDomains();
  renderStats();
  renderHomeDashboard();
  renderBrowse();
  renderReview();
  renderInterview();
  renderJobs();
  renderResumeReview();
  renderAccountCenter();
  updateNav();
  updateViewVisibility();
}

function renderAuthPanel() {
  const isLoggedIn = Boolean(state.currentUser);
  elements.authTabs.classList.toggle("hidden", isLoggedIn);
  elements.authLoggedOut.classList.toggle("hidden", isLoggedIn);
  elements.authLoggedOut.style.display = isLoggedIn ? "none" : "";
  elements.authLoggedIn.classList.toggle("hidden", !isLoggedIn);
  elements.authLoggedIn.style.display = isLoggedIn ? "" : "none";
  elements.showLoginTabBtn.classList.toggle("active", state.authMode === "login");
  elements.showRegisterTabBtn.classList.toggle("active", state.authMode === "register");
  elements.loginForm.classList.toggle("hidden", state.authMode !== "login");
  elements.registerForm.classList.toggle("hidden", state.authMode !== "register");

  if (isLoggedIn) {
    elements.currentUsername.textContent = state.currentUser.username || "已登录";
    elements.authStatus.textContent = `当前账号：${state.currentUser.username}。收藏、掌握和练习记录会同步到这个账号。`;
    return;
  }

  elements.authStatus.textContent =
    "用户名 4-20 位，仅支持字母、数字、下划线；密码至少 8 位，且至少包含大写字母、小写字母、数字、符号中的任意两类。";
}

function renderAccountCenter() {
  if (!state.currentUser) {
    elements.accountBadge.textContent = "未登录";
    elements.accountUserBox.textContent = "登录后可以查看账号概览、最近练习记录，并在这里修改密码。";
    elements.accountStats.innerHTML = "";
    elements.practiceSummary.textContent = "登录后查看最近练习情况";
    elements.accountRecords.innerHTML =
      '<div class="empty-mini"><h4>还没有登录</h4><p>先登录账号，再回来查看你的学习沉淀。</p></div>';
    elements.accountStatus.textContent = "登录后可修改密码，密码规则与注册时一致。";
    return;
  }

  const summary = buildAccountSummary();
  const records = buildRecentPracticeRecords();
  const storageLabel = state.progressApiAvailable ? "SQLite 数据库" : "本地兜底";
  const syncLabel = state.progressApiAvailable ? "已连接服务器" : "仅本地缓存";
  const createdAtLabel = formatBeijingTime(state.currentUser.createdAt || "");

  elements.accountBadge.textContent = state.currentUser.username;
  elements.accountUserBox.innerHTML = `
    <strong>${escapeHtml(state.currentUser.username)}</strong>
    <div class="record-meta">账号创建时间：${escapeHtml(createdAtLabel)}</div>
    <div class="record-meta">数据来源：${escapeHtml(storageLabel)} / 同步状态：${escapeHtml(syncLabel)}</div>
  `;
  elements.accountStats.innerHTML = [
    accountStatCard("收藏题目", summary.favoriteCount),
    accountStatCard("已掌握题目", summary.masteredCount),
    accountStatCard("练习总次数", summary.practiceTotal),
    accountStatCard("练过的题", summary.practicedQuestionCount),
  ].join("");

  elements.practiceSummary.textContent = records.length ? `最近 ${records.length} 条练习记录` : "还没有练习记录";
  elements.accountRecords.innerHTML = records.length
    ? records
        .map(
          (item) => `
            <article class="record-card" data-record-question="${escapeAttribute(item.questionId)}">
              <h5>${escapeHtml(item.question)}</h5>
              <div class="meta-row">
                <span class="pill">${escapeHtml(getDomainLabel(item.domain))}</span>
                <span class="pill">${escapeHtml(item.category || "other")}</span>
                <span class="pill">${escapeHtml(item.difficulty || "mid")}</span>
              ${item.favorite ? '<span class="pill accent">已收藏</span>' : ""}
              ${item.mastered ? '<span class="pill accent">已掌握</span>' : ""}
            </div>
              <p class="record-meta">练习次数：${escapeHtml(item.practiceCount)}，最近练习：${escapeHtml(formatBeijingTime(item.lastPracticedAt || ""))}</p>
            </article>
          `,
        )
        .join("")
    : '<div class="empty-mini"><h4>还没有练习记录</h4><p>先去刷题、模拟面试或随机练习，记录就会出现在这里。</p></div>';

  elements.accountRecords.querySelectorAll("[data-record-question]").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedQuestionId = card.dataset.recordQuestion;
      renderQuestionDetail(findSelectedQuestion());
      navigate("detail");
    });
  });
}

function renderDomains() {
  elements.domainSwitch.innerHTML = DOMAIN_DEFINITIONS.map((domain) => {
    const active = domain.value === state.selectedDomain;
    return `
      <button class="domain-btn ${active ? "active" : ""}" data-domain="${domain.value}">
        <strong>${escapeHtml(domain.label)}</strong>
        <span>${escapeHtml(domain.desc)}</span>
      </button>
    `;
  }).join("");

  elements.domainSwitch.querySelectorAll("[data-domain]").forEach((button) => {
    button.addEventListener("click", () => switchDomain(button.dataset.domain));
  });

  elements.heroStats.innerHTML = [
    statPill("题目总数", state.allQuestions.length),
    ...(state.visitorStats
      ? [
          statPill("访问次数", formatNumber(state.visitorStats.totalVisits || 0)),
          statPill("访客人数", formatNumber(state.visitorStats.uniqueVisitors || 0)),
        ]
      : []),
    ...DOMAIN_DEFINITIONS.filter((item) => countByDomain(item.value) > 0).map((item) =>
      statPill(item.label, countByDomain(item.value)),
    ),
  ].join("");

  elements.homeDomainGrid.innerHTML = DOMAIN_DEFINITIONS.map((domain) =>
    homeDomainCard(domain.value, domain.label, countByDomain(domain.value), domain.desc, countByDomain(domain.value) === 0),
  ).join("");

  elements.homeDomainGrid.querySelectorAll("[data-home-domain]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.disabled === "true") return;
      switchDomain(button.dataset.homeDomain);
      navigate("browse");
    });
  });
}

function navigate(view) {
  state.currentView = view;
  updateNav();
  updateViewVisibility();

  if (view === "detail") renderQuestionDetail(findSelectedQuestion());
  if (view === "interview") {
    ensureInterviewQuestion();
    renderInterview();
  }
  if (view === "jobs") renderJobs();
  if (view === "resume") renderResumeReview();
  if (view === "account") {
    renderAccountCenter();
    loadAccountOverview().catch((error) => console.warn("Failed to load account overview.", error));
  }
}

function updateNav() {
  elements.mainNav.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.currentView);
  });
}

function updateViewVisibility() {
  Object.entries(elements.views).forEach(([name, node]) => {
    node.classList.toggle("active", name === state.currentView);
  });
}

function switchDomain(domain) {
  state.selectedDomain = domain;
  state.selectedCategory = "all";
  state.selectedDifficulty = "all";
  state.search = "";
  state.selectedQuestionId = null;
  state.interviewQuestionId = null;
  elements.searchInput.value = "";
  elements.difficultyFilter.value = "all";
  render();
}

function renderBrowse() {
  applyFilters();
  renderCategoryList();
  renderQuestionList();
  elements.browseTitle.textContent = `${getDomainLabel(state.selectedDomain)}题库`;
  elements.resultCount.textContent = `${state.filteredQuestions.length} 题`;
}

function renderCategoryList() {
  const domainQuestions = state.allQuestions.filter((item) => item.domain === state.selectedDomain);
  const counts = domainQuestions.reduce((map, item) => {
    map[item.category] = (map[item.category] || 0) + 1;
    return map;
  }, {});

  const categories = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  elements.categoryList.innerHTML = [
    categoryButton("all", "全部分类", domainQuestions.length, state.selectedCategory === "all"),
    ...categories.map(([category, count]) => categoryButton(category, category, count, state.selectedCategory === category)),
  ].join("");

  elements.categoryList.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedCategory = button.dataset.category;
      renderBrowse();
    });
  });
}

function applyFilters() {
  let items = state.allQuestions.filter((item) => item.domain === state.selectedDomain);
  if (state.selectedCategory !== "all") items = items.filter((item) => item.category === state.selectedCategory);
  if (state.selectedDifficulty !== "all") items = items.filter((item) => item.difficulty === state.selectedDifficulty);
  if (state.search) {
    items = items.filter((item) => {
      const haystack = [item.question, item.category, item.summary, ...(item.tags || [])].join(" ").toLowerCase();
      return haystack.includes(state.search);
    });
  }
  state.filteredQuestions = items;
}

function renderQuestionList() {
  if (!state.filteredQuestions.length) {
    elements.questionList.innerHTML = `<div class="empty-mini"><h4>没有匹配的题目</h4><p>换个分类、难度或搜索词再试试。</p></div>`;
    return;
  }

  elements.questionList.innerHTML = state.filteredQuestions
    .map((item) => {
      const isFavorite = state.favorites.has(item.id);
      const isMastered = state.mastered.has(item.id);
      return `
        <article class="question-item" data-id="${item.id}">
          <h4>${escapeHtml(item.question)}</h4>
          <div class="meta-row">
            <span class="pill">${escapeHtml(item.category)}</span>
            <span class="pill">${escapeHtml(item.difficulty)}</span>
            ${isFavorite ? '<span class="pill accent">已收藏</span>' : ""}
            ${isMastered ? '<span class="pill accent">已掌握</span>' : ""}
          </div>
          <div class="tag-row">
            ${(item.tags || []).slice(0, 4).map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}
          </div>
          <button class="inline-link" type="button">查看详情</button>
        </article>
      `;
    })
    .join("");

  elements.questionList.querySelectorAll("[data-id]").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedQuestionId = card.dataset.id;
      markQuestionPracticed(card.dataset.id);
      renderQuestionDetail(findSelectedQuestion());
      navigate("detail");
    });
  });
}

function renderQuestionDetail(question) {
  if (!question) {
    elements.questionDetail.className = "detail-card empty-state";
    elements.questionDetail.innerHTML = `<h3>先选一道题</h3><p>从题库页进入，或者在首页点击“随机来一题”。</p>`;
    return;
  }

  const isFavorite = state.favorites.has(question.id);
  const isMastered = state.mastered.has(question.id);
  const currentIndex = findQuestionIndex(question.id);
  const prevQuestion = currentIndex > 0 ? state.filteredQuestions[currentIndex - 1] : null;
  const nextQuestion = currentIndex >= 0 && currentIndex < state.filteredQuestions.length - 1 ? state.filteredQuestions[currentIndex + 1] : null;
  const answerPoints = question.answerPoints || [];
  const followUps = question.followUps?.length ? question.followUps : ["可以继续追问实现细节、边界条件和实际应用场景。"];

  elements.questionDetail.className = "detail-card";
  elements.questionDetail.innerHTML = `
    <div class="detail-topbar">
      <button class="ghost-inline" id="backToBrowseBtn" type="button">返回题库</button>
    </div>
    <div class="detail-header">
      <div>
        <div class="detail-tags">
          <span class="pill">${escapeHtml(question.section)}</span>
          <span class="pill">${escapeHtml(question.category)}</span>
          <span class="pill">${escapeHtml(question.difficulty)}</span>
        </div>
        <h3>${escapeHtml(question.question)}</h3>
      </div>
      <div class="detail-actions">
        <button id="favoriteBtn" type="button">${isFavorite ? "取消收藏" : "收藏"}</button>
        <button id="masteredBtn" type="button">${isMastered ? "取消已掌握" : "标记已掌握"}</button>
      </div>
    </div>
    ${question.summary ? `<section class="detail-section"><div class="summary-box">${escapeHtml(question.summary)}</div></section>` : ""}
    <section class="detail-section">
      <h4>答案要点</h4>
      <ul>${answerPoints.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </section>
    <section class="detail-section">
      <h4>高频追问</h4>
      <ul>${followUps.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </section>
    <section class="detail-section">
      <h4>标签</h4>
      <div class="detail-tags">${(question.tags || []).map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}</div>
    </section>
    <section class="detail-section">
      <h4>来源</h4>
      <div class="meta-row">
        <span class="pill">${escapeHtml(question.sourceTitle || "题库导入")}</span>
        ${question.sourceUrl ? `<a class="pill anchor-link" href="${escapeAttribute(question.sourceUrl)}" target="_blank" rel="noreferrer">打开来源</a>` : ""}
      </div>
    </section>
    <section class="detail-section">
      <div class="pager-actions">
        <button id="prevQuestionBtn" type="button" ${prevQuestion ? "" : "disabled"}>上一题</button>
        <button id="nextQuestionBtn" type="button" ${nextQuestion ? "" : "disabled"}>下一题</button>
        <button id="enterInterviewBtn" type="button">用这题进入模拟面试</button>
      </div>
    </section>
  `;

  document.getElementById("backToBrowseBtn").addEventListener("click", () => navigate("browse"));
  document.getElementById("favoriteBtn").addEventListener("click", () => {
    updateQuestionStatus(question.id, { favorite: !state.favorites.has(question.id) });
    renderQuestionDetail(findSelectedQuestion());
  });
  document.getElementById("masteredBtn").addEventListener("click", () => {
    updateQuestionStatus(question.id, { mastered: !state.mastered.has(question.id) });
    renderQuestionDetail(findSelectedQuestion());
  });
  document.getElementById("prevQuestionBtn").addEventListener("click", () => {
    if (!prevQuestion) return;
    state.selectedQuestionId = prevQuestion.id;
    markQuestionPracticed(prevQuestion.id);
    renderQuestionDetail(prevQuestion);
  });
  document.getElementById("nextQuestionBtn").addEventListener("click", () => {
    if (!nextQuestion) return;
    state.selectedQuestionId = nextQuestion.id;
    markQuestionPracticed(nextQuestion.id);
    renderQuestionDetail(nextQuestion);
  });
  document.getElementById("enterInterviewBtn").addEventListener("click", () => {
    state.interviewQuestionId = question.id;
    state.interviewReveal = false;
    elements.interviewDraft.value = "";
    markQuestionPracticed(question.id);
    renderInterview();
    navigate("interview");
  });
}

function renderInterview() {
  ensureInterviewQuestion();
  const question = findInterviewQuestion();
  if (!question) return;

  const isFavorite = state.favorites.has(question.id);
  const isMastered = state.mastered.has(question.id);
  const followUps = question.followUps?.length ? question.followUps : ["可以继续追问实现细节、边界条件和实际应用场景。"];
  const savedAnswer = state.interviewAnswers[question.id]?.answer || "";

  elements.interviewMeta.innerHTML = `
    <span class="pill">${escapeHtml(question.section)}</span>
    <span class="pill">${escapeHtml(question.category)}</span>
    <span class="pill">${escapeHtml(question.difficulty)}</span>
  `;
  elements.interviewQuestion.textContent = question.question;
  if (elements.interviewDraft.dataset.questionId !== question.id || elements.interviewDraft.value !== savedAnswer) {
    elements.interviewDraft.dataset.questionId = question.id;
    elements.interviewDraft.value = savedAnswer;
  }
  if (elements.interviewAnswerStatus) {
    elements.interviewAnswerStatus.textContent = savedAnswer
      ? "你已经提交过这道题的回答，继续补充也会自动保存。"
      : "先自己作答，再点击提交回答。";
  }
  elements.interviewSubmitBtn.textContent = "提交回答";
  elements.markInterviewFavoriteBtn.textContent = isFavorite ? "取消收藏" : "收藏这道题";
  elements.markInterviewMasteredBtn.textContent = isMastered ? "取消已掌握" : "标记已掌握";
  elements.toggleInterviewAnswerBtn.textContent = state.interviewReveal ? "收起答案" : "展开答案";
  elements.interviewReveal.classList.toggle("hidden", !state.interviewReveal);
  elements.interviewAnswerPoints.innerHTML = (question.answerPoints || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  elements.interviewFollowUps.innerHTML = followUps.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderResumeReview() {
  if (!state.resumeReview) {
    elements.resumeResult.innerHTML = "";
    elements.resumeGenerated.innerHTML = "";
    elements.resumeFollowupActions.classList.add("hidden");
    return;
  }

  const review = state.resumeReview;
  const matched = review.jobMatch?.matchedKeywords || [];
  const missing = review.jobMatch?.missingKeywords || [];
  const dimensions = review.dimensionScores || [];
  const keywordExtraction = review.keywordExtraction || {};
  const detectedTechKeywords = keywordExtraction.detectedTechKeywords || [];
  const experienceSignals = keywordExtraction.experienceSignals || [];
  const aiFallbackReason = review.aiFallbackReason || "";

  elements.resumeResult.innerHTML = `
    <div class="resume-score-hero">
      <div class="resume-score-main"><span>综合评分</span><strong>${escapeHtml(review.overallScore ?? "-")}</strong></div>
      <div class="resume-score-side"><span>评审模式</span><strong>${escapeHtml(review.modeLabel || "未知")}</strong></div>
    </div>
    <section class="resume-section"><h4>总体结论</h4><p>${escapeHtml(review.summary || "暂无总体结论。")}</p></section>
    <section class="resume-section"><h4>岗位匹配度</h4><p><strong>目标岗位：</strong>${escapeHtml(review.jobMatch?.targetRole || "")}</p><div class="detail-tags">${renderPills(matched, true)}${renderPills(missing)}</div></section>
    ${(detectedTechKeywords.length || experienceSignals.length)
      ? `<section class="resume-section"><h4>识别到的简历信号</h4>${detectedTechKeywords.length ? `<div class="detail-tags">${renderPills(detectedTechKeywords, true)}</div>` : ""}${experienceSignals.length ? `<ul>${experienceSignals.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}</section>`
      : ""}
    ${aiFallbackReason ? `<section class="resume-section"><h4>AI 调用状态</h4><p>${escapeHtml(aiFallbackReason)}</p></section>` : ""}
    <section class="resume-section"><h4>多维评分</h4><div class="resume-dimension-grid">${dimensions.map((item) => `<article class="resume-dimension-card"><div class="resume-dimension-top"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.score)}</span></div><p class="resume-dimension-verdict">${escapeHtml(item.verdict || "")}</p><p>${escapeHtml(item.reasoning || "")}</p></article>`).join("")}</div></section>
    <section class="resume-section"><h4>优势亮点</h4><ul>${(review.strengths || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>
    <section class="resume-section"><h4>风险与改进</h4><ul>${(review.risks || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>
    <section class="resume-section"><h4>行动建议</h4><ul>${(review.suggestions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>
  `;

  elements.resumeFollowupActions.classList.remove("hidden");
  renderResumeGenerated();
}

function renderResumeGenerated() {
  const blocks = [];
  if (state.resumeRewrite) {
    blocks.push(`<section class="resume-section"><h4>改写建议</h4><p>${escapeHtml(state.resumeRewrite.summary || "")}</p>${renderGeneratedList("修改建议", state.resumeRewrite.rewritePoints || [])}${renderGeneratedList("可直接替换的表达", state.resumeRewrite.sampleBullets || [])}</section>`);
  }
  if (state.resumeInterviewPack) {
    blocks.push(`<section class="resume-section"><h4>基于简历的模拟题</h4>${renderGeneratedList("高频问题", state.resumeInterviewPack.questions || [])}${renderGeneratedList("重点追问", state.resumeInterviewPack.followUps || [])}</section>`);
  }
  elements.resumeGenerated.innerHTML = blocks.join("");
}

async function handleResumeReviewSubmit(event) {
  event.preventDefault();
  const resumeFile = elements.resumeFile.files[0];
  if (!resumeFile) {
    elements.resumeStatus.textContent = "请先上传简历文件再开始评审";
    return;
  }
  const formData = new FormData();
  formData.append("resume_file", resumeFile);
  formData.append("target_role", elements.resumeRole.value.trim());
  formData.append("target_stack", elements.resumeStack.value.trim());
  formData.append("target_jd", elements.resumeJd.value.trim());
  formData.append("selected_domain", state.selectedDomain);

  elements.resumeSubmitBtn.disabled = true;
  elements.resumeStatus.textContent = "正在评审简历...";
  try {
    const response = await fetch("/api/review-resume", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "简历评审失败");
    state.resumeReview = payload.review;
    state.resumeRewrite = null;
    state.resumeInterviewPack = null;
    elements.resumeStatus.textContent = payload.message || "评审完成";
    renderResumeReview();
  } catch (error) {
    elements.resumeStatus.textContent = `评审失败：${error.message}`;
  } finally {
    elements.resumeSubmitBtn.disabled = false;
  }
}

async function handleResumeRewrite() {
  if (!state.resumeReview?.resumeId) return;
  elements.generateRewriteBtn.disabled = true;
  elements.resumeStatus.textContent = "正在生成修改版简历建议...";
  try {
    const response = await fetch("/api/rewrite-resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_id: state.resumeReview.resumeId }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "生成修改版简历建议失败");
    state.resumeRewrite = payload.rewrite;
    elements.resumeStatus.textContent = payload.message || "已生成修改版简历建议。";
    renderResumeGenerated();
  } catch (error) {
    elements.resumeStatus.textContent = `生成失败：${error.message}`;
  } finally {
    elements.generateRewriteBtn.disabled = false;
  }
}

async function handleResumeInterviewPack() {
  if (!state.resumeReview?.resumeId) return;
  elements.generateInterviewPackBtn.disabled = true;
  elements.resumeStatus.textContent = "正在生成基于简历的模拟面试题...";
  try {
    const response = await fetch("/api/generate-resume-interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume_id: state.resumeReview.resumeId }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "生成模拟面试题失败");
    state.resumeInterviewPack = payload.interviewPack;
    elements.resumeStatus.textContent = payload.message || "已生成模拟面试题。";
    renderResumeGenerated();
  } catch (error) {
    elements.resumeStatus.textContent = `生成失败：${error.message}`;
  } finally {
    elements.generateInterviewPackBtn.disabled = false;
  }
}

function renderJobs() {
  const companies = state.jobsData.companies || [];
  const jobs = state.jobsData.jobs || [];

  const filteredJobs = jobs.filter((job) => {
    const track = inferJobTrack(job);
    if (state.selectedJobCompany !== "all" && job.company !== state.selectedJobCompany) return false;
    if (state.selectedJobTrack !== "all" && track !== state.selectedJobTrack) return false;
    if (!state.jobSearch) return true;
    const haystack = [job.company, job.title, job.city, job.type, job.summary, ...(job.keywords || []), ...(job.jd || [])]
      .join(" ")
      .toLowerCase();
    return haystack.includes(state.jobSearch);
  });

  elements.jobsMeta.innerHTML = [
    `<div class="jobs-meta-pill">公司数 ${companies.length}</div>`,
    `<div class="jobs-meta-pill">岗位快照 ${jobs.length}</div>`,
    `<div class="jobs-meta-pill">当前结果 ${filteredJobs.length}</div>`,
  ].join("");

  elements.jobsTrackFilters.innerHTML = JOB_TRACKS.map(
    (track) => `
      <button class="jobs-filter-chip ${state.selectedJobTrack === track.value ? "active" : ""}" data-job-track="${track.value}" type="button">
        ${escapeHtml(track.label)}
      </button>
    `,
  ).join("");

  elements.jobsTrackFilters.querySelectorAll("[data-job-track]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedJobTrack = button.dataset.jobTrack;
      renderJobs();
    });
  });

  elements.jobsCompanyGrid.innerHTML = companies
    .map(
      (company) => `
        <article class="company-card ${state.selectedJobCompany === company.name ? "is-active" : ""}">
          <div class="company-card-head"><strong>${escapeHtml(company.name)}</strong><span>${escapeHtml(company.tagline)}</span></div>
          <p>${escapeHtml(company.desc)}</p>
          <div class="company-actions">
            <a class="inline-link anchor-link" href="${escapeAttribute(company.campusUrl)}" target="_blank" rel="noreferrer">校招入口</a>
            <a class="inline-link anchor-link" href="${escapeAttribute(company.socialUrl)}" target="_blank" rel="noreferrer">社招入口</a>
            <button class="ghost-inline" data-company-pick="${escapeAttribute(company.name)}" type="button">${state.selectedJobCompany === company.name ? "清除筛选" : "筛选本公司"}</button>
          </div>
        </article>
      `,
    )
    .join("");

  elements.jobsList.innerHTML = filteredJobs.length
    ? filteredJobs
        .map(
          (job, index) => `
            <article class="job-card">
              <div class="job-head">
                <div>
                  <div class="detail-tags">
                    <span class="pill">${escapeHtml(job.company)}</span>
                    <span class="pill">${escapeHtml(job.city)}</span>
                    <span class="pill">${escapeHtml(job.type)}</span>
                  </div>
                  <h4>${escapeHtml(job.title)}</h4>
                </div>
                <a class="inline-link anchor-link" href="${escapeAttribute(job.applyUrl)}" target="_blank" rel="noreferrer">一键跳转</a>
              </div>
              <div class="tag-row">${(job.keywords || []).map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}</div>
              <p class="job-summary">${escapeHtml(job.summary)}</p>
              <button class="ghost-inline" data-job-toggle="${index}" type="button">展开 JD</button>
              <div class="job-jd hidden" id="job-jd-${index}">${(job.jd || []).map((item) => `<p>${escapeHtml(item)}</p>`).join("")}</div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-mini"><h4>没有匹配的岗位快照</h4><p>换个公司、岗位、关键词再试试。</p></div>`;

  elements.jobsList.querySelectorAll("[data-job-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(`job-jd-${button.dataset.jobToggle}`);
      const isHidden = target.classList.toggle("hidden");
      button.textContent = isHidden ? "展开 JD" : "收起 JD";
    });
  });

  elements.jobsCompanyGrid.querySelectorAll("[data-company-pick]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const company = button.dataset.companyPick;
      state.selectedJobCompany = state.selectedJobCompany === company ? "all" : company;
      renderJobs();
    });
  });
}

function renderReview() {
  const favorites = state.allQuestions.filter((item) => state.favorites.has(item.id));
  const mastered = state.allQuestions.filter((item) => state.mastered.has(item.id));

  elements.favoritesLabel.textContent = `${favorites.length} 题`;
  elements.masteredLabel.textContent = `${mastered.length} 题`;
  elements.favoritesList.innerHTML = renderReviewCards(favorites, "还没有收藏题");
  elements.masteredList.innerHTML = renderReviewCards(mastered, "还没有已掌握题");
  bindReviewCards(elements.favoritesList);
  bindReviewCards(elements.masteredList);
}

function renderReviewCards(items, emptyText) {
  if (!items.length) {
    return `<div class="empty-mini"><h4>${escapeHtml(emptyText)}</h4><p>先去题库页选题，再回来复习。</p></div>`;
  }

  return items
    .map(
      (item) => `
        <article class="question-item compact-card" data-id="${item.id}">
          <h4>${escapeHtml(item.question)}</h4>
          <div class="meta-row">
            <span class="pill">${escapeHtml(item.section)}</span>
            <span class="pill">${escapeHtml(item.category)}</span>
          </div>
        </article>
      `,
    )
    .join("");
}

function bindReviewCards(container) {
  container.querySelectorAll("[data-id]").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedQuestionId = card.dataset.id;
      markQuestionPracticed(card.dataset.id);
      renderQuestionDetail(findSelectedQuestion());
      navigate("detail");
    });
  });
}

function renderStats() {
  elements.favoriteCount.textContent = state.favorites.size;
  elements.masteredCount.textContent = state.mastered.size;
}

function renderHomeDashboard() {
  const domains = DOMAIN_DEFINITIONS.filter((item) => item.value !== "cs_basic");
  const activeDomain = state.selectedDomain || "frontend";

  if (elements.homeSearchInput) {
    elements.homeSearchInput.value = state.search || "";
  }

  elements.homeFeaturedTabs.innerHTML = domains
    .map((domain) => {
      const active = domain.value === activeDomain;
      return `<button class="home-featured-tab ${active ? "active" : ""}" type="button" data-home-tab="${escapeAttribute(domain.value)}">${escapeHtml(domain.label)}</button>`;
    })
    .join("");

  elements.homeFeaturedTabs.querySelectorAll("[data-home-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedDomain = button.dataset.homeTab;
      renderHomeDashboard();
      renderDomains();
    });
  });

  const featuredQuestions = state.allQuestions.filter((item) => item.domain === activeDomain).slice(0, 3);
  elements.homeFeaturedList.innerHTML = featuredQuestions
    .map(
      (item) => `
        <button class="home-question-card" type="button" data-home-question="${escapeAttribute(item.id)}">
          <div class="home-question-head">
            <div class="home-question-title">
              ${renderIcon(domainIconName(item.domain), "home-question-icon")}
              <strong>${escapeHtml(item.question)}</strong>
            </div>
            <span class="home-question-difficulty">${escapeHtml(item.difficulty || "mid")}</span>
          </div>
          <p>${escapeHtml(item.summary || item.category || "精选题目")}</p>
          <div class="home-question-meta">
            <span class="pill">${escapeHtml(item.category || "other")}</span>
            <span class="pill">${escapeHtml(item.sourceTitle || "题库导入")}</span>
          </div>
        </button>
      `,
    )
    .join("");

  elements.homeFeaturedList.querySelectorAll("[data-home-question]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedQuestionId = button.dataset.homeQuestion;
      markQuestionPracticed(button.dataset.homeQuestion);
      renderQuestionDetail(findSelectedQuestion());
      navigate("detail");
    });
  });

  const summary = buildAccountSummary();
  const records = buildRecentPracticeRecords().slice(0, 3);

  if (!state.currentUser) {
    elements.homeAccountBox.innerHTML = `
      <strong>未登录</strong>
      <div class="record-meta">登录后同步收藏、掌握和练习记录</div>
      <div class="home-account-actions">
        <button class="auth-submit home-account-login-btn" type="button">登录后同步</button>
      </div>
    `;
    elements.homeAccountBox.querySelector(".home-account-login-btn")?.addEventListener("click", () => navigate("account"));
  } else {
    elements.homeAccountBox.innerHTML = `
      <strong>${escapeHtml(state.currentUser.username)}</strong>
      <div class="record-meta">收藏 ${escapeHtml(summary.favoriteCount)} 题 · 已掌握 ${escapeHtml(summary.masteredCount)} 题 · 练习 ${escapeHtml(summary.practiceTotal)} 次</div>
      <div class="record-meta">账户时间：${escapeHtml(formatBeijingTime(state.currentUser.createdAt || ""))}</div>
    `;
  }

  elements.homeRecordList.innerHTML = records.length
    ? records
        .map(
          (item) => `
            <button class="home-record-item" type="button" data-home-record="${escapeAttribute(item.questionId)}">
              <div class="home-record-main">
                ${renderIcon(domainIconName(item.domain), "home-record-icon")}
                <div class="home-record-copy">
                  <strong>${escapeHtml(item.question)}</strong>
                  <div class="record-meta">${escapeHtml(getDomainLabel(item.domain))} · ${escapeHtml(item.category || "other")} · ${escapeHtml(item.difficulty || "mid")}</div>
                </div>
              </div>
              <div class="home-record-side">
                <span>${escapeHtml(item.practiceCount)} 次</span>
                <small>${escapeHtml(formatBeijingTime(item.lastPracticedAt || ""))}</small>
              </div>
            </button>
          `,
        )
        .join("")
    : '<div class="empty-mini"><h4>还没有练习记录</h4><p>开始刷题或进入模拟面试后，这里会出现最近记录。</p></div>';

  elements.homeRecordList.querySelectorAll("[data-home-record]").forEach((button) => {
    button.addEventListener("click", () => {
      const questionId = button.dataset.homeRecord;
      state.selectedQuestionId = questionId;
      markQuestionPracticed(questionId);
      renderQuestionDetail(findSelectedQuestion());
      navigate("detail");
    });
  });
}

function rerenderQuestionState() {
  renderStats();
  renderHomeDashboard();
  renderBrowse();
  renderReview();
  renderInterview();
  renderAccountCenter();
}

function openRandomQuestion() {
  const pool = state.allQuestions.filter((item) => item.domain === state.selectedDomain);
  if (!pool.length) return;
  const random = pool[Math.floor(Math.random() * pool.length)];
  state.selectedQuestionId = random.id;
  markQuestionPracticed(random.id);
  renderQuestionDetail(random);
  navigate("detail");
}

function performHomeSearch(rawQuery) {
  const query = String(rawQuery || "").trim().toLowerCase();
  if (!query) return;

  state.search = query;

  const jobMatch = findBestJobMatch(query);
  const questionMatch = findBestQuestionMatch(query);
  const resumeHints = ["简历", "评审", "改写", "面试", "resume", "cv"];
  const isResumeQuery = resumeHints.some((hint) => query.includes(hint));

  if (jobMatch && (!questionMatch || jobMatch.score >= questionMatch.score + 2)) {
    state.selectedJobCompany = "all";
    state.selectedJobTrack = inferJobTrack(jobMatch.item);
    state.jobSearch = query;
    navigate("jobs");
    renderJobs();
    return;
  }

  if (questionMatch) {
    state.selectedQuestionId = questionMatch.item.id;
    state.selectedDomain = questionMatch.item.domain || state.selectedDomain;
    state.selectedCategory = "all";
    state.selectedDifficulty = "all";
    navigate(questionMatch.score >= 8 ? "detail" : "browse");
    if (state.currentView === "detail") {
      renderQuestionDetail(questionMatch.item);
      return;
    }
    renderBrowse();
    return;
  }

  if (isResumeQuery) {
    navigate("review");
    return;
  }

  navigate("browse");
  renderBrowse();
}

function scoreQuestionMatch(query, item) {
  const fields = [
    { text: item.question, weight: 8 },
    { text: item.summary, weight: 4 },
    { text: item.category, weight: 3 },
    { text: item.section, weight: 3 },
    { text: item.sourceTitle, weight: 2 },
    { text: Array.isArray(item.tags) ? item.tags.join(" ") : "", weight: 4 },
  ];
  let score = 0;
  for (const field of fields) {
    const value = String(field.text || "").toLowerCase();
    if (value.includes(query)) score += field.weight;
  }
  return score;
}

function findBestQuestionMatch(query) {
  let best = null;
  for (const item of state.allQuestions) {
    const score = scoreQuestionMatch(query, item);
    if (score <= 0) continue;
    if (!best || score > best.score) {
      best = { item, score };
    }
  }
  return best;
}

function scoreJobMatch(query, job) {
  const fields = [
    { text: job.company, weight: 6 },
    { text: job.title, weight: 8 },
    { text: job.city, weight: 2 },
    { text: job.type, weight: 2 },
    { text: job.summary, weight: 3 },
    { text: Array.isArray(job.keywords) ? job.keywords.join(" ") : "", weight: 5 },
    { text: Array.isArray(job.jd) ? job.jd.join(" ") : "", weight: 2 },
  ];
  let score = 0;
  for (const field of fields) {
    const value = String(field.text || "").toLowerCase();
    if (value.includes(query)) score += field.weight;
  }
  return score;
}

function findBestJobMatch(query) {
  const jobs = state.jobsData.jobs || [];
  let best = null;
  for (const job of jobs) {
    const score = scoreJobMatch(query, job);
    if (score <= 0) continue;
    if (!best || score > best.score) {
      best = { item: job, score };
    }
  }
  return best;
}

function chooseRandomInterviewQuestion() {
  const pool = state.allQuestions.filter((item) => item.domain === state.selectedDomain);
  if (!pool.length) return;
  const random = pool[Math.floor(Math.random() * pool.length)];
  state.interviewQuestionId = random.id;
  state.interviewReveal = false;
  elements.interviewDraft.value = "";
}

function ensureInterviewQuestion() {
  if (!findInterviewQuestion()) chooseRandomInterviewQuestion();
}

function findSelectedQuestion() {
  return state.allQuestions.find((item) => item.id === state.selectedQuestionId) || null;
}

function findInterviewQuestion() {
  return state.allQuestions.find((item) => item.id === state.interviewQuestionId) || null;
}

function findQuestionIndex(id) {
  return state.filteredQuestions.findIndex((item) => item.id === id);
}

function countByDomain(domain) {
  return state.allQuestions.filter((item) => item.domain === domain).length;
}

function getDomainLabel(domain) {
  const match = DOMAIN_DEFINITIONS.find((item) => item.value === domain);
  return match ? match.label : "题库";
}

function inferJobTrack(job) {
  const haystack = [job.title, ...(job.keywords || []), job.summary].join(" ").toLowerCase();
  if (haystack.includes("测试")) return "testing";
  if (haystack.includes("算法") || haystack.includes("推荐") || haystack.includes("机器学习")) return "algorithm";
  if (haystack.includes("运维") || haystack.includes("云原生") || haystack.includes("kubernetes") || haystack.includes("docker")) return "ops";
  if (haystack.includes("前端") || haystack.includes("react") || haystack.includes("vue")) return "frontend";
  if (haystack.includes("后端") || haystack.includes("java") || haystack.includes("go") || haystack.includes("分布式")) return "backend";
  if (haystack.includes("ai") || haystack.includes("大模型") || haystack.includes("rag") || haystack.includes("agent") || haystack.includes("prompt")) return "ai_app";
  return "all";
}

function statPill(label, value) {
  const iconName =
    label.includes("访问") ? "trend" :
    label.includes("访客") ? "users" :
    label.includes("前端") ? "monitor" :
    label.includes("后端") ? "db" :
    label.includes("AI") ? "spark" :
    label.includes("测试") ? "flask" :
    label.includes("算法") ? "target" :
    "book";
  return `
    <div class="hero-pill">
      <div class="hero-pill-top">
        ${renderIcon(iconName, "hero-pill-icon")}
        <span>${escapeHtml(label)}</span>
      </div>
      <strong>${value}</strong>
    </div>
  `;
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

function formatBeijingTime(value) {
  if (!value) return "暂无";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "暂无";
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function categoryButton(value, label, count, active) {
  return `<button class="category-btn ${active ? "active" : ""}" data-category="${value}" type="button">${escapeHtml(label)} <span>(${count})</span></button>`;
}

function homeDomainCard(value, label, count, desc, disabled = false) {
  return `
    <button class="domain-card" data-home-domain="${value}" data-disabled="${disabled}" type="button">
      <div class="domain-card-head">
        <div class="domain-card-title">
          ${renderIcon(domainIconName(value), "domain-card-icon")}
          <strong>${escapeHtml(label)}</strong>
        </div>
        <span>${disabled ? "待接入" : `${count} 题`}</span>
      </div>
      <p>${escapeHtml(desc)}</p>
    </button>
  `;
}

function renderGeneratedList(title, items = []) {
  if (!items.length) return "";
  const renderedItems = items
    .map((item) => {
      if (item == null) return "";
      if (typeof item === "string" || typeof item === "number") {
        return `<li>${escapeHtml(String(item))}</li>`;
      }
      if (Array.isArray(item)) {
        const text = item
          .map((entry) => (entry == null ? "" : typeof entry === "object" ? entry.question || entry.title || entry.text || entry.content || "" : String(entry)))
          .filter(Boolean)
          .join(" / ");
        return text ? `<li>${escapeHtml(text)}</li>` : "";
      }
      if (typeof item === "object") {
        const primary = item.question || item.title || item.text || item.content || item.label || "";
        const meta = [item.intent, Array.isArray(item.answerTips) ? item.answerTips.filter(Boolean).join("；") : ""].filter(Boolean);
        return `
          <li>
            <strong>${escapeHtml(String(primary || "未命名条目"))}</strong>
            ${meta.length ? `<div class="generated-list-meta">${escapeHtml(meta.join(" · "))}</div>` : ""}
          </li>
        `;
      }
      return `<li>${escapeHtml(String(item))}</li>`;
    })
    .filter(Boolean)
    .join("");

  return `<div class="generated-list-block"><h5>${escapeHtml(title)}</h5><ul>${renderedItems}</ul></div>`;
}

function renderPills(items = [], accent = false) {
  if (!items.length) return "";
  return items.map((item) => `<span class="pill ${accent ? "accent" : ""}">${escapeHtml(item)}</span>`).join("");
}

function switchAuthMode(mode) {
  state.authMode = mode === "register" ? "register" : "login";
  renderAuthPanel();
}

async function loadAccountOverview() {
  if (!state.currentUser) {
    state.accountOverview = null;
    renderAccountCenter();
    return null;
  }

  try {
    const response = await fetch("/api/account/overview");
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "加载个人中心失败");
    state.accountOverview = payload;
    renderAccountCenter();
    return payload;
  } catch (error) {
    elements.accountStatus.textContent = error.message;
    throw error;
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const username = elements.loginUsername.value.trim();
  const password = elements.loginPassword.value;
  if (!username || !password) {
    elements.authStatus.textContent = "请输入用户名和密码。";
    return;
  }

  setAuthSubmitting(true);
  elements.authStatus.textContent = "正在登录...";
  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "登录失败");

    applyAuthState(payload);
    applyUserProgress(payload.progress || null);
    applyInterviewAnswers(await loadInterviewAnswers());
    state.accountOverview = null;
    await loadAccountOverview().catch(() => null);
    elements.loginForm.reset();
    render();
    elements.authStatus.textContent = payload.message || "登录成功";
  } catch (error) {
    elements.authStatus.textContent = error.message;
  } finally {
    setAuthSubmitting(false);
  }
}

async function handleRegisterSubmit(event) {
  event.preventDefault();
  const username = elements.registerUsername.value.trim();
  const password = elements.registerPassword.value;
  const confirmPassword = elements.registerConfirmPassword.value;
  if (!username || !password || !confirmPassword) {
    elements.authStatus.textContent = "请完整填写注册信息。";
    return;
  }

  setAuthSubmitting(true);
  elements.authStatus.textContent = "正在注册...";
  try {
    const response = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, confirmPassword }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "注册失败");

    applyAuthState(payload);
    applyUserProgress(payload.progress || null);
    applyInterviewAnswers(await loadInterviewAnswers());
    state.accountOverview = null;
    await loadAccountOverview().catch(() => null);
    elements.registerForm.reset();
    render();
    elements.authStatus.textContent = payload.message || "注册成功";
  } catch (error) {
    elements.authStatus.textContent = error.message;
  } finally {
    setAuthSubmitting(false);
  }
}

async function handleLogout() {
  setAuthSubmitting(true);
  try {
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "退出失败");

    const [authState, userProgress] = await Promise.all([loadAuthState(), loadUserProgress()]);
    applyAuthState(authState);
    applyUserProgress(userProgress);
    applyInterviewAnswers(await loadInterviewAnswers());
    state.accountOverview = null;
    render();
    elements.authStatus.textContent = payload.message || "已退出登录";
  } catch (error) {
    elements.authStatus.textContent = error.message;
  } finally {
    setAuthSubmitting(false);
  }
}

async function handleChangePassword(event) {
  event.preventDefault();
  if (!state.currentUser) {
    elements.accountStatus.textContent = "请先登录后再修改密码。";
    return;
  }

  const currentPassword = elements.currentPasswordInput.value;
  const newPassword = elements.newPasswordInput.value;
  const confirmPassword = elements.confirmPasswordInput.value;
  if (!currentPassword || !newPassword || !confirmPassword) {
    elements.accountStatus.textContent = "请完整填写当前密码和新密码。";
    return;
  }

  elements.changePasswordBtn.disabled = true;
  elements.accountStatus.textContent = "正在更新密码...";
  try {
    const response = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ currentPassword, newPassword, confirmPassword }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "修改密码失败");
    elements.changePasswordForm.reset();
    elements.accountStatus.textContent = payload.message || "密码修改成功";
  } catch (error) {
    elements.accountStatus.textContent = error.message;
  } finally {
    elements.changePasswordBtn.disabled = false;
  }
}

function setAuthSubmitting(submitting) {
  [
    elements.showLoginTabBtn,
    elements.showRegisterTabBtn,
    ...elements.loginForm.querySelectorAll("input, button"),
    ...elements.registerForm.querySelectorAll("input, button"),
    elements.logoutBtn,
  ].forEach((node) => {
    node.disabled = submitting;
  });
}

function accountStatCard(label, value) {
  return `<div class="account-stat"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function loadSet(key) {
  try {
    const raw = localStorage.getItem(key);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function persistLocalSet(key, set) {
  localStorage.setItem(key, JSON.stringify([...set]));
}

function loadPracticeMap(key) {
  try {
    const raw = localStorage.getItem(key);
    const payload = raw ? JSON.parse(raw) : {};
    return normalizePracticeMap(payload);
  } catch {
    return {};
  }
}

function loadJsonMap(key) {
  try {
    const raw = localStorage.getItem(key);
    const payload = raw ? JSON.parse(raw) : {};
    return payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
  } catch {
    return {};
  }
}

function persistJsonMap(key, value) {
  localStorage.setItem(key, JSON.stringify(value || {}));
}

function getInterviewAnswersStorageKey() {
  if (state.currentUser?.id) {
    return `mvp_interview_answers_user_${state.currentUser.id}`;
  }
  return "mvp_interview_answers_visitor";
}

function loadInterviewAnswersLocalMap() {
  const scopedKey = getInterviewAnswersStorageKey();
  const scopedPayload = normalizeInterviewAnswerMap(loadJsonMap(scopedKey));
  if (Object.keys(scopedPayload).length) {
    return scopedPayload;
  }

  if (state.currentUser?.id) {
    return {};
  }

  const legacyPayload = normalizeInterviewAnswerMap(loadJsonMap("mvp_interview_answers"));
  if (Object.keys(legacyPayload).length) {
    persistInterviewAnswersLocalMap(legacyPayload);
  }
  return legacyPayload;
}

function persistInterviewAnswersLocalMap(interviewAnswers) {
  localStorage.setItem(getInterviewAnswersStorageKey(), JSON.stringify(interviewAnswers || {}));
}

function normalizeInterviewAnswerMap(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return {};
  return Object.entries(payload).reduce((result, [questionId, item]) => {
    if (typeof item === "string") {
      result[questionId] = { answer: item, updatedAt: "" };
      return result;
    }
    result[questionId] = {
      answer: String(item?.answer || ""),
      updatedAt: String(item?.updatedAt || ""),
    };
    return result;
  }, {});
}

function mergeInterviewAnswerMaps(serverAnswers, localAnswers) {
  const merged = normalizeInterviewAnswerMap(serverAnswers);
  for (const [questionId, item] of Object.entries(normalizeInterviewAnswerMap(localAnswers))) {
    const current = merged[questionId];
    if (!current) {
      merged[questionId] = item;
      continue;
    }
    if (String(item.updatedAt || "") > String(current.updatedAt || "")) {
      merged[questionId] = item;
    }
  }
  return merged;
}

function hasInterviewAnswerDeficit(mergedAnswers, serverAnswers) {
  const normalizedServer = normalizeInterviewAnswerMap(serverAnswers);
  return Object.entries(normalizeInterviewAnswerMap(mergedAnswers)).some(([questionId, item]) => {
    const serverItem = normalizedServer[questionId];
    if (!serverItem) {
      return Boolean(item.answer);
    }
    return String(item.updatedAt || "") > String(serverItem.updatedAt || "");
  });
}

function clearInterviewAnswerTimers() {
  for (const timer of state.interviewAnswerSyncTimers.values()) {
    clearTimeout(timer);
  }
  state.interviewAnswerSyncTimers.clear();
}

function clearInterviewAnswerSyncTimer(questionId) {
  const timer = state.interviewAnswerSyncTimers.get(questionId);
  if (timer) {
    clearTimeout(timer);
    state.interviewAnswerSyncTimers.delete(questionId);
  }
}

function updateInterviewAnswerCache(questionId, answer, updatedAt = new Date().toISOString()) {
  state.interviewAnswers[questionId] = {
    answer: String(answer || ""),
    updatedAt,
  };
  persistInterviewAnswersLocalMap(state.interviewAnswers);
  return state.interviewAnswers[questionId];
}

function scheduleInterviewAnswerSync(questionId, record) {
  if (!state.interviewApiAvailable) return;
  clearInterviewAnswerSyncTimer(questionId);
  const timer = setTimeout(() => {
    state.interviewAnswerSyncTimers.delete(questionId);
    persistInterviewAnswerToServer(questionId, record.answer, record.updatedAt).catch((error) => {
      console.warn("Failed to sync interview answer draft.", error);
    });
  }, 500);
  state.interviewAnswerSyncTimers.set(questionId, timer);
}

async function persistInterviewAnswerToServer(questionId, answer, updatedAt = new Date().toISOString()) {
  if (!state.interviewApiAvailable) return;
  const response = await fetch("/api/interview-answers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      questionId,
      answer,
      updatedAt,
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "Failed to persist interview answer");
  }
}

async function syncInterviewAnswersToServer(interviewAnswers) {
  if (!state.interviewApiAvailable) return;
  for (const [questionId, item] of Object.entries(normalizeInterviewAnswerMap(interviewAnswers))) {
    await persistInterviewAnswerToServer(questionId, item.answer, item.updatedAt);
  }
}

function persistPracticeMap(key, practiceMap) {
  localStorage.setItem(key, JSON.stringify(practiceMap));
}

function normalizePracticeMap(payload) {
  if (!payload || typeof payload !== "object") return {};
  return Object.entries(payload).reduce((result, [questionId, item]) => {
    result[questionId] = {
      practiceCount: Number(item?.practiceCount || 0),
      lastPracticedAt: String(item?.lastPracticedAt || ""),
    };
    return result;
  }, {});
}

function mergePracticeMaps(serverPractice, localPractice) {
  const merged = normalizePracticeMap(serverPractice);
  for (const [questionId, item] of Object.entries(normalizePracticeMap(localPractice))) {
    const existing = merged[questionId] || { practiceCount: 0, lastPracticedAt: "" };
    const timestamps = [String(existing.lastPracticedAt || ""), String(item.lastPracticedAt || "")].filter(Boolean);
    const lastPracticedAt = timestamps.length ? timestamps.sort()[timestamps.length - 1] : "";
    merged[questionId] = {
      practiceCount: Math.max(Number(existing.practiceCount || 0), Number(item.practiceCount || 0)),
      lastPracticedAt,
    };
  }
  return merged;
}

function buildAccountSummary() {
  const serverSummary = state.accountOverview?.summary || {};
  const practiceTotal = Object.values(state.practice || {}).reduce((total, item) => total + Number(item.practiceCount || 0), 0);
  const practicedQuestionCount = Object.keys(state.practice || {}).length;
  return {
    favoriteCount: Math.max(Number(serverSummary.favoriteCount || 0), state.favorites.size),
    masteredCount: Math.max(Number(serverSummary.masteredCount || 0), state.mastered.size),
    practiceTotal: Math.max(Number(serverSummary.practiceTotal || 0), practiceTotal),
    practicedQuestionCount: Math.max(Number(serverSummary.practicedQuestionCount || 0), practicedQuestionCount),
  };
}

function buildRecentPracticeRecords() {
  const serverRecords = Array.isArray(state.accountOverview?.recentPractice) ? state.accountOverview.recentPractice : [];
  if (serverRecords.length) {
    return serverRecords;
  }

  return Object.entries(state.practice || {})
    .filter(([, item]) => Number(item.practiceCount || 0) > 0)
    .map(([questionId, item]) => {
      const question = state.allQuestions.find((entry) => entry.id === questionId);
      return {
        questionId,
        question: question?.question || questionId,
        domain: question?.domain || "other",
        section: question?.section || "",
        category: question?.category || "",
        difficulty: question?.difficulty || "mid",
        favorite: state.favorites.has(questionId),
        mastered: state.mastered.has(questionId),
        practiceCount: Number(item.practiceCount || 0),
        lastPracticedAt: item.lastPracticedAt || "",
      };
    })
    .sort((left, right) => (right.lastPracticedAt || "").localeCompare(left.lastPracticedAt || ""));
}

function hasPracticeDeficit(mergedPractice, serverPractice) {
  const normalizedServerPractice = normalizePracticeMap(serverPractice);
  return Object.entries(normalizePracticeMap(mergedPractice)).some(([questionId, item]) => {
    const serverCount = Number(normalizedServerPractice[questionId]?.practiceCount || 0);
    return Number(item.practiceCount || 0) > serverCount;
  });
}

function updateQuestionStatus(questionId, updates = {}) {
  if ("favorite" in updates) {
    if (updates.favorite) state.favorites.add(questionId);
    else state.favorites.delete(questionId);
    persistLocalSet("mvp_favorites", state.favorites);
  }

  if ("mastered" in updates) {
    if (updates.mastered) state.mastered.add(questionId);
    else state.mastered.delete(questionId);
    persistLocalSet("mvp_mastered", state.mastered);
  }

  rerenderQuestionState();
  persistQuestionStatus(questionId, updates).catch((error) => {
    console.warn("Failed to persist question status.", error);
  });
}

async function persistQuestionStatus(questionId, updates = {}) {
  if (!state.progressApiAvailable) return;
  const response = await fetch("/api/user-progress", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ questionId, ...updates }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "Failed to persist progress");
  }
}

async function syncProgressToServer() {
  if (!state.progressApiAvailable) return;
  const response = await fetch("/api/user-progress/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      favorites: [...state.favorites],
      mastered: [...state.mastered],
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "Failed to sync progress");
  }
}

async function syncPracticeToServer(mergedPractice, serverPractice = {}) {
  if (!state.progressApiAvailable || !state.currentUser) return;

  const normalizedServerPractice = normalizePracticeMap(serverPractice);
  for (const [questionId, item] of Object.entries(normalizePracticeMap(mergedPractice))) {
    const localCount = Number(item.practiceCount || 0);
    const serverCount = Number(normalizedServerPractice[questionId]?.practiceCount || 0);
    const deficit = localCount - serverCount;
    for (let index = 0; index < deficit; index += 1) {
      await persistQuestionStatus(questionId, { practiced: true });
    }
  }
}

function markQuestionPracticed(questionId) {
  if (state.practicedThisSession.has(questionId)) return;
  state.practicedThisSession.add(questionId);

  const current = state.practice[questionId] || { practiceCount: 0, lastPracticedAt: "" };
  state.practice[questionId] = {
    practiceCount: Number(current.practiceCount || 0) + 1,
    lastPracticedAt: new Date().toISOString(),
  };
  persistPracticeMap("mvp_practice", state.practice);
  renderAccountCenter();

  persistQuestionStatus(questionId, { practiced: true }).catch((error) => {
    console.warn("Failed to persist practice record.", error);
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}

const ICON_PATHS = {
  book: `
    <path d="M7 5.5c2.8 0 4.5.8 5 1.9v11.1c-.5-1.1-2.2-1.9-5-1.9-1.4 0-2.8.2-4 .7V7.4c1.2-.5 2.6-.7 4-.7Z"/>
    <path d="M17 5.5c-2.8 0-4.5.8-5 1.9v11.1c.5-1.1 2.2-1.9 5-1.9 1.4 0 2.8.2 4 .7V7.4c-1.2-.5-2.6-.7-4-.7Z"/>
    <path d="M12 7.1v11.2"/>
  `,
  trend: `
    <path d="M4.5 15.5 9 11l3.3 3.3L19.5 7"/>
    <path d="M15.8 7H19.5v3.7"/>
  `,
  users: `
    <path d="M9.2 10.1a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8Z"/>
    <path d="M14.9 10.1a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/>
    <path d="M4.8 17.2c.6-2.5 2.4-3.8 4.4-3.8s3.9 1.3 4.4 3.8"/>
    <path d="M14.5 14c1.5.2 2.7 1.1 3.4 2.9"/>
  `,
  monitor: `
    <rect x="4.2" y="5.8" width="15.6" height="10.2" rx="2.2"/>
    <path d="M9.3 18.2h5.4"/>
    <path d="M12 15.8v2.4"/>
  `,
  db: `
    <ellipse cx="12" cy="6.1" rx="6.8" ry="2.9"/>
    <path d="M5.2 6.1v5.4c0 1.6 3 2.9 6.8 2.9s6.8-1.3 6.8-2.9V6.1"/>
    <path d="M5.2 11.5c0 1.6 3 2.9 6.8 2.9s6.8-1.3 6.8-2.9"/>
    <path d="M5.2 16.9c0 1.6 3 2.9 6.8 2.9s6.8-1.3 6.8-2.9"/>
  `,
  spark: `
    <path d="M12 4.6 13.9 9l4.4 1.9-4.4 1.9L12 17.2 10.1 12.8 5.7 10.9l4.4-1.9L12 4.6Z"/>
  `,
  flask: `
    <path d="M9 4.8h6"/>
    <path d="M10.4 4.8v4.2L6.3 16a2 2 0 0 0 1.8 3h8a2 2 0 0 0 1.8-3l-4.1-7v-4.2"/>
    <path d="M8.1 13.8h7.8"/>
  `,
  compass: `
    <circle cx="12" cy="12" r="7.3"/>
    <path d="m15.8 8.2-1.5 4.7-4.6 1.5 1.5-4.7 4.6-1.5Z"/>
  `,
  clock: `
    <circle cx="12" cy="12" r="7.4"/>
    <path d="M12 8.2v4l2.7 1.8"/>
  `,
  target: `
    <circle cx="12" cy="12" r="7"/>
    <circle cx="12" cy="12" r="2.4"/>
  `,
  refresh: `
    <path d="M20 12a8 8 0 1 1-2.3-5.7"/>
    <path d="M20 5.8v4.3h-4.3"/>
  `,
};

function renderIcon(name, className = "") {
  const paths = ICON_PATHS[name] || ICON_PATHS.book;
  return `
    <span class="ui-icon ${escapeHtml(className)}" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none">
        ${paths}
      </svg>
    </span>
  `;
}

function domainIconName(domain) {
  switch (domain) {
    case "frontend":
      return "monitor";
    case "backend":
      return "db";
    case "ai_app":
      return "spark";
    case "testing":
      return "flask";
    case "algorithm":
      return "target";
    case "ops":
      return "compass";
    default:
      return "book";
  }
}
