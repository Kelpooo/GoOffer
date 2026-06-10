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
  selectedDomain: "frontend",
  selectedCategory: "all",
  selectedDifficulty: "all",
  search: "",
  selectedQuestionId: null,
  currentView: "home",
  interviewQuestionId: null,
  interviewReveal: false,
  jobsData: { companies: [], jobs: [] },
  jobSearch: "",
  selectedJobCompany: "all",
  selectedJobTrack: "all",
  resumeReview: null,
  resumeRewrite: null,
  resumeInterviewPack: null,
  favorites: loadSet("mvp_favorites"),
  mastered: loadSet("mvp_mastered"),
};

const elements = {
  mainNav: document.getElementById("mainNav"),
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
  toggleInterviewAnswerBtn: document.getElementById("toggleInterviewAnswerBtn"),
  markInterviewFavoriteBtn: document.getElementById("markInterviewFavoriteBtn"),
  markInterviewMasteredBtn: document.getElementById("markInterviewMasteredBtn"),
  interviewReveal: document.getElementById("interviewReveal"),
  interviewAnswerPoints: document.getElementById("interviewAnswerPoints"),
  interviewFollowUps: document.getElementById("interviewFollowUps"),
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
  },
};

bootstrap();

async function bootstrap() {
  const [questionsResponse, jobsResponse, visitorStats] = await Promise.all([
    fetch("./data/questions.json"),
    fetch("./data/jobs.json"),
    fetch("/api/site-stats")
      .then((response) => response.json())
      .catch(() => ({ ok: false })),
  ]);

  const questionsPayload = await questionsResponse.json();
  const jobsPayload = await jobsResponse.json();

  state.allQuestions = questionsPayload.questions || [];
  state.jobsData = jobsPayload || { companies: [], jobs: [] };
  state.visitorStats = visitorStats?.ok ? visitorStats : null;

  bindEvents();
  render();
}

function bindEvents() {
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
    navigate("interview");
  });
  elements.goResumeBtn.addEventListener("click", () => navigate("resume"));
  elements.goReviewBtn.addEventListener("click", () => navigate("review"));
  elements.randomFromHomeBtn.addEventListener("click", openRandomQuestion);
  elements.randomQuestionBtn.addEventListener("click", openRandomQuestion);

  elements.refreshInterviewBtn.addEventListener("click", () => {
    chooseRandomInterviewQuestion();
    renderInterview();
  });

  elements.toggleInterviewAnswerBtn.addEventListener("click", () => {
    state.interviewReveal = !state.interviewReveal;
    renderInterview();
  });

  elements.markInterviewFavoriteBtn.addEventListener("click", () => {
    const question = findInterviewQuestion();
    if (!question) return;
    toggleSetValue(state.favorites, question.id, "mvp_favorites");
    rerenderQuestionState();
  });

  elements.markInterviewMasteredBtn.addEventListener("click", () => {
    const question = findInterviewQuestion();
    if (!question) return;
    toggleSetValue(state.mastered, question.id, "mvp_mastered");
    rerenderQuestionState();
  });

  elements.resumeForm.addEventListener("submit", handleResumeReviewSubmit);
  elements.generateRewriteBtn.addEventListener("click", handleResumeRewrite);
  elements.generateInterviewPackBtn.addEventListener("click", handleResumeInterviewPack);
}

function render() {
  renderDomains();
  renderStats();
  renderBrowse();
  renderReview();
  renderInterview();
  renderJobs();
  renderResumeReview();
  updateNav();
  updateViewVisibility();
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
    toggleSetValue(state.favorites, question.id, "mvp_favorites");
    rerenderQuestionState();
    renderQuestionDetail(findSelectedQuestion());
  });
  document.getElementById("masteredBtn").addEventListener("click", () => {
    toggleSetValue(state.mastered, question.id, "mvp_mastered");
    rerenderQuestionState();
    renderQuestionDetail(findSelectedQuestion());
  });
  document.getElementById("prevQuestionBtn").addEventListener("click", () => {
    if (!prevQuestion) return;
    state.selectedQuestionId = prevQuestion.id;
    renderQuestionDetail(prevQuestion);
  });
  document.getElementById("nextQuestionBtn").addEventListener("click", () => {
    if (!nextQuestion) return;
    state.selectedQuestionId = nextQuestion.id;
    renderQuestionDetail(nextQuestion);
  });
  document.getElementById("enterInterviewBtn").addEventListener("click", () => {
    state.interviewQuestionId = question.id;
    state.interviewReveal = false;
    elements.interviewDraft.value = "";
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

  elements.interviewMeta.innerHTML = `
    <span class="pill">${escapeHtml(question.section)}</span>
    <span class="pill">${escapeHtml(question.category)}</span>
    <span class="pill">${escapeHtml(question.difficulty)}</span>
  `;
  elements.interviewQuestion.textContent = question.question;
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

  elements.resumeResult.innerHTML = `
    <div class="resume-score-hero">
      <div class="resume-score-main"><span>综合评分</span><strong>${escapeHtml(review.overallScore ?? "-")}</strong></div>
      <div class="resume-score-side"><span>评审模式</span><strong>${escapeHtml(review.modeLabel || "未知")}</strong></div>
    </div>
    <section class="resume-section"><h4>总体结论</h4><p>${escapeHtml(review.summary || "暂无总体结论。")}</p></section>
    <section class="resume-section"><h4>岗位匹配度</h4><p><strong>目标岗位：</strong>${escapeHtml(review.jobMatch?.targetRole || "")}</p><div class="detail-tags">${renderPills(matched, true)}${renderPills(missing)}</div></section>
    <section class="resume-section"><h4>多维评分</h4><div class="resume-dimension-grid">${dimensions.map((item) => `<article class="resume-dimension-card"><div class="resume-dimension-top"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.score)}</span></div><p class="resume-dimension-verdict">${escapeHtml(item.verdict || "")}</p><p>${escapeHtml(item.reason || "")}</p></article>`).join("")}</div></section>
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
  const formData = new FormData();
  formData.append("resume_file", elements.resumeFile.files[0]);
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
      renderQuestionDetail(findSelectedQuestion());
      navigate("detail");
    });
  });
}

function renderStats() {
  elements.favoriteCount.textContent = state.favorites.size;
  elements.masteredCount.textContent = state.mastered.size;
}

function rerenderQuestionState() {
  renderStats();
  renderBrowse();
  renderReview();
  renderInterview();
}

function openRandomQuestion() {
  const pool = state.allQuestions.filter((item) => item.domain === state.selectedDomain);
  if (!pool.length) return;
  const random = pool[Math.floor(Math.random() * pool.length)];
  state.selectedQuestionId = random.id;
  renderQuestionDetail(random);
  navigate("detail");
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
  return `<div class="hero-pill"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

function categoryButton(value, label, count, active) {
  return `<button class="category-btn ${active ? "active" : ""}" data-category="${value}" type="button">${escapeHtml(label)} <span>(${count})</span></button>`;
}

function homeDomainCard(value, label, count, desc, disabled = false) {
  return `
    <button class="domain-card" data-home-domain="${value}" data-disabled="${disabled}" type="button">
      <div class="domain-card-head">
        <strong>${escapeHtml(label)}</strong>
        <span>${disabled ? "待接入" : `${count} 题`}</span>
      </div>
      <p>${escapeHtml(desc)}</p>
    </button>
  `;
}

function renderGeneratedList(title, items = []) {
  if (!items.length) return "";
  return `<div class="generated-list-block"><h5>${escapeHtml(title)}</h5><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>`;
}

function renderPills(items = [], accent = false) {
  if (!items.length) return "";
  return items.map((item) => `<span class="pill ${accent ? "accent" : ""}">${escapeHtml(item)}</span>`).join("");
}

function loadSet(key) {
  try {
    const raw = localStorage.getItem(key);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function toggleSetValue(set, value, key) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
  localStorage.setItem(key, JSON.stringify([...set]));
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
