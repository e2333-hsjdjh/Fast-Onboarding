const basePath = document.querySelector('script[src$="app.js"]').getAttribute('src').replace(/\/static\/app\.js$/, '');

const $ = (id) => document.getElementById(id);
const state = {
  experiences: [],
  projects: [],
  currentUser: null,
  session: null,
  activeProject: null,
  sourceCategory: 'basic',
  experienceAiDraft: []
};

const sessionKey = 'fastOnboarding.session';
const categoryLabels = {
  basic: '基础信息',
  education: '教育经历',
  work: '工作经历',
  experience: '工作经历',
  project: '项目经历',
  award: '获得奖项',
  skill: '技能与特长',
  other: '其他'
};
const resumeSectionTargets = {
  basic: 'summary',
  education: 'educationText',
  work: 'workResumeText',
  experience: 'workResumeText',
  project: 'projectResumeText',
  award: 'awardResumeText',
  skill: 'skills',
  other: 'otherResumeText'
};

const experienceTemplates = {
  basic: {
    title: '基础信息模板',
    hint: '用于确认身份、求职方向、联系方式和个人定位。这里的信息会优先进入简历页眉与个人摘要。',
    fields: [
      ['legal_name', '真实姓名', 'input', '与证件或简历一致的姓名'],
      ['preferred_name', '常用称呼/英文名', 'input', '可选'],
      ['target_role', '目标岗位', 'input', '例如 AI 产品经理'],
      ['target_industry', '目标行业', 'input', '例如 AI 应用、教育科技、企业服务'],
      ['city', '当前城市/期望城市', 'input', '例如 上海 / 北京 / 远程'],
      ['email', '邮箱', 'input', '用于简历展示'],
      ['phone', '电话', 'input', '用于简历展示'],
      ['portfolio', '作品集/个人网站', 'input', 'URL'],
      ['github', 'GitHub', 'input', 'URL 或用户名'],
      ['linkedin', 'LinkedIn/脉脉/其他主页', 'input', 'URL'],
      ['availability', '到岗时间', 'input', '例如 2 周内、随时'],
      ['work_authorization', '工作身份/签证情况', 'input', '如适用'],
      ['summary_positioning', '一句话定位', 'textarea', '用事实描述你是谁、擅长什么、适合什么岗位'],
      ['core_strengths', '核心优势关键词', 'textarea', '每行一个关键词，尽量可被经历证明']
    ]
  },
  education: {
    title: '教育经历模板',
    hint: '记录学校、专业、课程、论文、荣誉和可验证证明，方便筛选与岗位相关的教育背景。',
    fields: [
      ['school', '学校/学院', 'input', '学校全称'],
      ['degree', '学历/学位', 'input', '本科 / 硕士 / 博士 / 交换等'],
      ['major', '专业', 'input', '主修专业'],
      ['minor', '辅修/方向', 'input', '可选'],
      ['start_date', '开始时间', 'input', 'YYYY.MM'],
      ['end_date', '结束时间', 'input', 'YYYY.MM 或 至今'],
      ['gpa_rank', 'GPA/排名', 'input', '如真实且有优势再填写'],
      ['core_courses', '相关课程', 'textarea', '与目标岗位相关的课程，每行一个'],
      ['thesis_research', '论文/研究/毕业设计', 'textarea', '题目、方法、结果、导师或项目背景'],
      ['campus_roles', '校园职务/社团', 'textarea', '职责、规模、结果'],
      ['honors', '校内荣誉', 'textarea', '奖学金、竞赛、荣誉称号'],
      ['education_proof', '证明材料', 'textarea', '成绩单、证书、项目链接等']
    ]
  },
  work: {
    title: '工作经历模板',
    hint: '工作经历要尽量写清业务背景、职责范围、动作、协作对象、指标和证明，避免空泛职责描述。',
    fields: [
      ['company', '公司/组织', 'input', '公司全称'],
      ['department', '部门/团队', 'input', '可选'],
      ['role', '岗位/职级', 'input', '例如 产品实习生 / 增长产品经理'],
      ['employment_type', '类型', 'input', '实习 / 全职 / 兼职 / 志愿等'],
      ['start_date', '开始时间', 'input', 'YYYY.MM'],
      ['end_date', '结束时间', 'input', 'YYYY.MM 或 至今'],
      ['business_context', '业务背景', 'textarea', '产品/业务是什么，用户是谁，核心问题是什么'],
      ['responsibilities', '职责范围', 'textarea', '你负责的模块、权限边界、交付物'],
      ['actions', '关键行动', 'textarea', '每行一个动作，使用动词开头'],
      ['results', '结果与指标', 'textarea', '转化率、效率、收入、留存、成本、规模等真实数字'],
      ['team_collaboration', '协作对象', 'textarea', '工程、设计、运营、销售、客户等'],
      ['tools_methods', '工具与方法', 'textarea', 'SQL、Python、A/B、访谈、原型、埋点等'],
      ['difficulty', '难点与解决', 'textarea', '限制条件、冲突、取舍和解决方式'],
      ['work_evidence', '证明材料', 'textarea', '文档、截图、链接、推荐人、公开记录等']
    ]
  },
  project: {
    title: '项目经历模板',
    hint: '项目经历适合展示问题定义、方案设计、个人贡献、技术/产品方法和结果证据。',
    fields: [
      ['project_name', '项目名称', 'input', '项目/产品/系统名称'],
      ['project_role', '你的角色', 'input', '负责人 / 产品 / 开发 / 数据分析等'],
      ['project_period', '项目周期', 'input', 'YYYY.MM-YYYY.MM'],
      ['project_context', '项目背景', 'textarea', '为什么做，服务谁，痛点是什么'],
      ['target_users', '目标用户/场景', 'textarea', '用户画像、使用场景、频次'],
      ['problem', '核心问题', 'textarea', '待解决的问题和判断依据'],
      ['solution', '解决方案', 'textarea', '方案架构、功能模块、流程设计'],
      ['personal_contribution', '个人贡献', 'textarea', '你具体做了什么，不要写团队泛称'],
      ['tech_stack', '技术/工具栈', 'textarea', '模型、框架、语言、平台、工具'],
      ['collaboration', '协作与管理', 'textarea', '沟通机制、分工、里程碑、风险管理'],
      ['result_metrics', '结果指标', 'textarea', '效率、用户、收入、准确率、通过率等'],
      ['project_links', '项目链接', 'textarea', 'GitHub、Demo、文档、作品集'],
      ['project_evidence', '证明材料', 'textarea', '提交记录、截图、用户反馈、证书等']
    ]
  },
  award: {
    title: '获得奖项模板',
    hint: '奖项要记录授予方、级别、评选标准和与你目标岗位的关系，避免只写奖项名。',
    fields: [
      ['award_name', '奖项名称', 'input', '奖项全称'],
      ['issuer', '授予方', 'input', '机构/学校/公司/赛事主办方'],
      ['award_level', '级别', 'input', '国家级/省级/校级/公司级等'],
      ['award_date', '获奖时间', 'input', 'YYYY.MM'],
      ['rank_percentile', '排名/比例', 'input', '如 Top 5%、一等奖/300 队'],
      ['selection_criteria', '评选标准', 'textarea', '依据什么评选，竞争规模如何'],
      ['related_work', '相关作品/贡献', 'textarea', '你因为什么成果获奖'],
      ['skills_reflected', '体现能力', 'textarea', '数据、产品、研究、领导力等'],
      ['award_relevance', '岗位相关性', 'textarea', '为什么对目标岗位有加分'],
      ['award_certificate', '证书/证明链接', 'textarea', '证书编号、URL、截图说明']
    ]
  },
  skill: {
    title: '技能与特长模板',
    hint: '技能不要只堆关键词，要补充熟练度、使用场景、工具、作品和证明。',
    fields: [
      ['skill_group', '技能类别', 'input', '产品 / 数据 / AI / 设计 / 语言等'],
      ['skill_items', '具体技能', 'textarea', '每行一个技能'],
      ['proficiency', '熟练度', 'input', '熟悉 / 熟练 / 精通，需有证据支撑'],
      ['years_or_frequency', '使用年限/频率', 'input', '例如 2 年 / 每周使用'],
      ['use_cases', '使用场景', 'textarea', '在哪些项目/工作中用过'],
      ['tools_platforms', '工具与平台', 'textarea', 'SQL、Python、Figma、DeepSeek、GitHub 等'],
      ['certifications', '证书/考试', 'textarea', '证书名、分数、时间'],
      ['representative_outputs', '代表产出', 'textarea', '作品、报告、系统、分析结果'],
      ['skill_evidence', '证明材料', 'textarea', '链接、截图、证书编号、仓库等']
    ]
  },
  other: {
    title: '其他经历模板',
    hint: '用于补充志愿、社群、内容创作、创业、开源、讲座等不适合放入前几类但可证明能力的经历。',
    fields: [
      ['experience_type', '经历类型', 'input', '志愿 / 社群 / 开源 / 内容 / 创业 / 其他'],
      ['other_title', '经历名称', 'input', '活动/组织/作品名称'],
      ['role', '你的角色', 'input', '组织者 / 贡献者 / 作者等'],
      ['period', '时间范围', 'input', 'YYYY.MM-YYYY.MM'],
      ['context', '背景与目标', 'textarea', '为什么做，服务谁，目标是什么'],
      ['contribution', '具体贡献', 'textarea', '你做了什么，投入多少，承担什么责任'],
      ['outcome', '结果与影响', 'textarea', '人数、阅读、Star、反馈、转化、影响范围等'],
      ['transferable_skills', '可迁移能力', 'textarea', '沟通、领导、研究、写作、执行等'],
      ['relevance', '与目标岗位相关性', 'textarea', '如何支撑当前岗位申请'],
      ['other_links', '链接/证明材料', 'textarea', 'URL、截图、公开记录、证明人等']
    ]
  }
};

const universalExperienceQuestions = [
  '发生在哪里？',
  '你是什么身份？',
  '时间是什么时候？',
  '背景/问题是什么？',
  '你的任务是什么？',
  '你做了哪些动作？',
  '用了什么工具或方法？',
  '最终产出了什么？',
  '结果怎么样？',
  '有没有数字证明？',
  '和目标岗位有什么关系？'
];

const bulletFormulaHints = [
  '通过【方法/工具】完成【任务】，实现【结果】',
  '针对【问题】，优化【方案】，使【指标】提升/降低【数字】',
  '使用【工具】分析【数据对象】，识别【问题/机会】，输出【建议】',
  '基于【技术/框架】开发【系统/功能】，实现【功能效果】'
];

function splitValues(text) {
  return text.split(/[,，、\n]/).map((item) => item.trim()).filter(Boolean);
}

function openUserExperiences() {
  if (!state.currentUser) return;
  showWorkspaceView('editor');
  setSourceCategory('basic');
  $('status').textContent = '正在编辑个人经历';
}

function showWorkspaceView(view) {
  const showEditor = view === 'editor';
  $('resumeLibrary').hidden = showEditor;
  $('resumeEditor').hidden = !showEditor;
  document.body.classList.toggle('resume-editor-active', showEditor);
  $('workspaceTitle').textContent = showEditor ? resumeTitle() : 'FastOnboarding';
  $('topCreateResumeBtn').hidden = !showEditor;
  $('topAddExperienceBtn').hidden = !showEditor;
  $('versionHistoryBtn').hidden = !showEditor;
  $('exportBtn').hidden = !showEditor;
}

function resumeTitle(project = state.activeProject) {
  if (!project) return '未命名公司-未命名岗位';
  return `${project.company_name || '未命名公司'}-${project.role_title || '未命名岗位'}`;
}

function createNewResume() {
  requireUser();
  $('newResumeCompany').value = '';
  $('newResumeRole').value = $('targetTitle') ? $('targetTitle').value || '' : '';
  $('newResumeTitle').value = '';
  $('newResumeJd').value = '';
  $('newResumeDialog').showModal();
}

async function submitNewResume() {
  const companyName = $('newResumeCompany').value.trim();
  const roleTitle = $('newResumeRole').value.trim();
  if (!companyName || !roleTitle) {
    $('status').textContent = '请填写公司名称和目标岗位';
    return;
  }
  const button = $('submitNewResumeBtn');
  button.disabled = true;
  try {
    const data = await requestJson(`/api/users/${encodeURIComponent(activeUserId())}/projects`, {
      method: 'POST',
      body: JSON.stringify({
        user_name: $('name').value,
        company_name: companyName,
        role_title: roleTitle,
        document_title: $('newResumeTitle').value.trim() || `${companyName}-${roleTitle}`,
        template_id: $('newResumeTemplate').value,
        language: $('newResumeLanguage').value,
        visibility: $('newResumeVisibility').value,
        jd_text: $('newResumeJd').value.trim(),
        status: 'draft',
        notes: '',
        resume_content: { sections: {} },
        change_summary: '创建简历'
      })
    });
    if ($('newResumeDialog').open) $('newResumeDialog').close();
    await loadUserWorkspace(activeUserId());
    activateProject(data.project);
    $('status').textContent = '新简历已创建';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function openVersionHistory() {
  if (!state.activeProject) {
    $('status').textContent = '请先创建或打开一份简历';
    return;
  }
  const list = $('versionHistoryList');
  list.innerHTML = '';
  try {
    const data = await requestJson(`/api/users/${encodeURIComponent(activeUserId())}/projects/${encodeURIComponent(state.activeProject.project_id)}/versions`);
    for (const version of data.versions || []) {
      const item = document.createElement('li');
      const title = document.createElement('strong');
      title.textContent = `版本 ${version.version_number}`;
      const meta = document.createElement('span');
      meta.className = 'record-meta';
      meta.textContent = `${version.change_summary || '保存简历'} · ${version.created_at}`;
      const restore = document.createElement('button');
      restore.type = 'button';
      restore.className = 'insert-experience-btn';
      restore.textContent = '恢复此版本';
      restore.addEventListener('click', () => restoreVersion(version.version_id));
      item.append(title, meta, restore);
      list.appendChild(item);
    }
    if (!list.childElementCount) list.textContent = '还没有可恢复版本。';
    $('versionHistoryDialog').showModal();
  } catch (error) {
    $('status').textContent = error.message;
  }
}

async function restoreVersion(versionId) {
  try {
    const data = await requestJson(`/api/users/${encodeURIComponent(activeUserId())}/projects/${encodeURIComponent(state.activeProject.project_id)}/restore`, {
      method: 'POST',
      body: JSON.stringify({ version_id: versionId })
    });
    await loadUserWorkspace(activeUserId());
    activateProject(data.project);
    if ($('versionHistoryDialog').open) $('versionHistoryDialog').close();
    $('status').textContent = '已恢复历史版本，并创建新的当前版本';
  } catch (error) {
    $('status').textContent = error.message;
  }
}

function activeUserId() {
  return (state.currentUser ? state.currentUser.user_id : '').trim().toLowerCase().replace(/\s+/g, '-');
}

function requireUser() {
  if (!state.currentUser) {
    throw new Error('请先登录');
  }
  return state.currentUser;
}

function setAuthMode(mode) {
  const isLogin = mode !== 'register';
  $('loginForm').classList.toggle('hidden', !isLogin);
  $('registerForm').classList.toggle('hidden', isLogin);
  $('showLoginBtn').classList.toggle('active', isLogin);
  $('showRegisterBtn').classList.toggle('active', !isLogin);
  $('authStatus').textContent = isLogin ? '请输入账号进入工作区。' : '创建账号后会自动进入工作区。';
}

function applyUserToProfile(user) {
  $('userId').value = user.user_id || '';
  $('name').value = user.name || $('name').value;
  $('email').value = user.email || $('email').value;
  $('targetTitle').value = user.target_title || $('targetTitle').value;
  $('phone').value = user.phone || $('phone').value;
  $('location').value = user.location || $('location').value;
  $('savedUser').textContent = user.user_id || '未保存';
}

async function activateUser(user, session = null) {
  state.currentUser = user;
  state.session = session || state.session;
  if (state.session) localStorage.setItem(sessionKey, JSON.stringify(state.session));
  $('authGate').hidden = true;
  $('workspace').hidden = false;
  $('userBadge').hidden = false;
  $('logoutBtn').hidden = false;
  $('userAvatar').textContent = user.avatar_initials || 'U';
  $('userNameLabel').textContent = user.name || user.email || user.user_id;
  $('resetTestAccountBtn').hidden = !user.is_test;
  applyUserToProfile(user);
  renderExperiences();
  renderProjects();
  await loadUserWorkspace(user.user_id);
  showWorkspaceView('library');
}

function logout() {
  state.currentUser = null;
  state.session = null;
  state.experiences = [];
  state.projects = [];
  state.activeProject = null;
  localStorage.removeItem(sessionKey);
  $('authGate').hidden = false;
  $('workspace').hidden = true;
  $('userBadge').hidden = true;
  $('logoutBtn').hidden = true;
  $('savedUser').textContent = '未保存';
  $('resetTestAccountBtn').hidden = true;
  renderExperiences();
  renderProjects();
  setAuthMode('login');
}

async function register(event) {
  event.preventDefault();
  $('authStatus').textContent = '创建账号中';
  try {
    const data = await requestJson('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: $('registerName').value,
        email: $('registerEmail').value,
        password: $('registerPassword').value,
        target_title: $('registerTargetTitle').value
      })
    });
    await activateUser(data.user, data.session);
    $('status').textContent = '账号已创建';
  } catch (error) {
    $('authStatus').textContent = error.message;
  }
}

async function login(event) {
  event.preventDefault();
  $('authStatus').textContent = '登录中';
  try {
    const data = await requestJson('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: $('loginEmail').value,
        password: $('loginPassword').value
      })
    });
    await activateUser(data.user, data.session);
    $('status').textContent = '已登录';
  } catch (error) {
    $('authStatus').textContent = error.message;
  }
}

async function restoreSession() {
  const raw = localStorage.getItem(sessionKey);
  if (!raw) {
    await loginTestAccount();
    return;
  }
  try {
    const stored = JSON.parse(raw);
    const data = await requestJson(`/api/auth/session/${encodeURIComponent(stored.token)}`);
    await activateUser(data.user, stored);
  } catch (error) {
    logout();
  }
}

async function loginTestAccount() {
  try {
    const data = await requestJson('/api/auth/test-session', { method: 'POST', body: JSON.stringify({}) });
    await activateUser(data.user, data.session);
    $('status').textContent = '已进入 test 测试账号';
  } catch (error) {
    $('authStatus').textContent = error.message;
  }
}

async function resetTestAccount() {
  if (!state.currentUser || !state.currentUser.is_test) return;
  const button = $('resetTestAccountBtn');
  button.disabled = true;
  try {
    const data = await requestJson('/api/auth/test-reset', { method: 'POST', body: JSON.stringify({}) });
    state.experiences = [];
    state.projects = data.projects || [];
    state.activeProject = null;
    applyUserToProfile(data.user);
    renderExperiences();
    renderProjects();
    showWorkspaceView('library');
    $('status').textContent = 'test 数据已重置为演示内容';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function currentExperiencePayload() {
  const templateData = currentTemplateData();
  const category = $('experienceCategory').value;
  return {
    user_name: $('name').value,
    category,
    template_key: category,
    title: $('experienceTitle').value || deriveTemplateTitle(category, templateData),
    organization: $('experienceOrg').value || deriveTemplateOrganization(category, templateData),
    bullets: buildTemplateBullets(category, templateData).concat($('experienceBullets').value.split('\n').map((line) => line.trim()).filter(Boolean)),
    metrics: $('experienceMetrics').value.split('\n').map((line) => line.trim()).filter(Boolean),
    skills: splitValues($('experienceSkills').value),
    template_data: templateData,
    evidence: collectTemplateEvidence(templateData)
  };
}

function currentProjectPayload() {
  return {
    user_name: $('name').value,
    company_name: $('companyName').value,
    role_title: $('projectRole').value,
    jd_text: $('jdText').value,
    status: $('projectStatus').value,
    notes: $('projectNotes').value,
    document_title: state.activeProject ? state.activeProject.document_title : '',
    template_id: state.activeProject ? state.activeProject.template_id : 'zsc_table_resume',
    language: state.activeProject ? state.activeProject.language : 'zh-CN',
    visibility: state.activeProject ? state.activeProject.visibility : 'private',
    selected_material_ids: state.experiences.map((item) => item.material_id || item.experience_id),
    resume_content: {
      name: $('name').value,
      target_title: $('targetTitle').value,
      summary: $('summary').value,
      education: $('educationText').value,
      work: $('workResumeText').value,
      projects: $('projectResumeText').value,
      awards: $('awardResumeText').value,
      skills: $('skills').value,
      other: $('otherResumeText').value
    },
    editor_preferences: { view: 'three-pane' },
    export_settings: { formats: ['docx', 'pdf'] },
    change_summary: '保存工作区编辑'
  };
}

function workspaceContext() {
  return {
    user: {
      name: $('name').value,
      target_title: $('targetTitle').value,
      email: $('email').value,
      phone: $('phone').value,
      location: $('location').value,
      summary: $('summary').value,
      skills: splitValues($('skills').value)
    },
    experience: currentExperiencePayload(),
    project: currentProjectPayload(),
    saved_experiences: state.experiences,
    saved_projects: state.projects,
    jd_text: $('jdText').value,
    target_title: $('projectRole').value || $('targetTitle').value
  };
}

function profilePayload() {
  const saved = state.experiences.length > 0 ? state.experiences : [currentExperiencePayload()];
  const experiences = saved.filter((item) => !['project', 'education', 'award', 'skill', 'other', 'basic'].includes(normalizeCategory(item.category))).map(toResumeExperience);
  const projects = saved.filter((item) => item.category === 'project').map(toResumeExperience);
  return {
    name: $('name').value,
    target_title: $('projectRole').value || $('targetTitle').value,
    email: $('email').value,
    phone: $('phone').value,
    location: $('location').value,
    summary: $('summary').value,
    skills: splitValues($('skills').value),
    experiences,
    projects,
    education: splitValues($('educationText').value)
  };
}

function normalizeCategory(category) {
  if (category === 'experience') return 'work';
  return category || 'work';
}

function currentTemplateData() {
  const data = {};
  document.querySelectorAll('[data-template-field]').forEach((field) => {
    data[field.dataset.templateField] = field.value.trim();
  });
  return data;
}

function deriveTemplateTitle(category, data) {
  const keys = {
    basic: 'target_role',
    education: 'school',
    work: 'role',
    project: 'project_name',
    award: 'award_name',
    skill: 'skill_group',
    other: 'other_title'
  };
  return data[keys[normalizeCategory(category)]] || categoryLabels[normalizeCategory(category)] || '未命名经历';
}

function deriveTemplateOrganization(category, data) {
  const keys = {
    basic: 'city',
    education: 'school',
    work: 'company',
    project: 'project_role',
    award: 'issuer',
    skill: 'tools_platforms',
    other: 'experience_type'
  };
  return data[keys[normalizeCategory(category)]] || '';
}

function buildTemplateBullets(category, data) {
  const template = experienceTemplates[normalizeCategory(category)];
  if (!template) return [];
  return template.fields
    .map(([key, label]) => [label, data[key]])
    .filter(([, value]) => value)
    .map(([label, value]) => `${label}：${value}`);
}

function collectTemplateEvidence(data) {
  const evidenceKeys = [
    'education_proof',
    'work_evidence',
    'project_links',
    'project_evidence',
    'award_certificate',
    'skill_evidence',
    'other_links',
    'portfolio',
    'github',
    'linkedin'
  ];
  return evidenceKeys.flatMap((key) => splitValues(data[key] || ''));
}

function toResumeExperience(item) {
  return {
    title: item.title,
    organization: item.organization,
    start: item.start || '',
    end: item.end || '',
    bullets: item.bullets || [],
    metrics: item.metrics || [],
    skills: item.skills || []
  };
}

function renderList(id, items, emptyText) {
  const target = $(id);
  target.innerHTML = '';
  if (!items || items.length === 0) {
    target.textContent = emptyText;
    return;
  }
  for (const item of items) {
    if (id === 'missing') {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = item;
      target.appendChild(chip);
    } else {
      const li = document.createElement('li');
      li.textContent = item;
      target.appendChild(li);
    }
  }
}

function renderExperiences() {
  $('experienceCount').textContent = String(state.experiences.length);
  const list = $('experienceList');
  list.innerHTML = '';
  const selected = normalizeCategory(state.sourceCategory);
  const filtered = state.experiences.filter((item) => normalizeCategory(item.category) === selected);
  $('sourceDetailTitle').textContent = categoryLabels[selected] || '经历';
  if (filtered.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'empty-record';
    empty.textContent = '这个分类还没有经历。点击上方“添加经历”录入。';
    list.appendChild(empty);
    return;
  }
  for (const item of filtered) {
    const li = document.createElement('li');
    const title = document.createElement('strong');
    title.textContent = item.title || '未命名经历';
    const meta = document.createElement('span');
    meta.className = 'record-meta';
    meta.textContent = `${item.organization || '未填写组织'} · ${categoryLabels[normalizeCategory(item.category)] || '经历'} · ${(item.skills || []).join('、') || '无技能标签'}`;
    const insert = document.createElement('button');
    insert.type = 'button';
    insert.className = 'insert-experience-btn';
    insert.textContent = '插入简历';
    insert.addEventListener('click', () => insertExperienceToResume(item));
    li.append(title, meta, insert);
    list.appendChild(li);
  }
}

function renderProjects() {
  $('projectCount').textContent = String(state.projects.length);
  const list = $('projectList');
  list.innerHTML = '';
  for (const item of state.projects) {
    const li = document.createElement('li');
    const title = document.createElement('strong');
    title.textContent = `${item.company_name || '未填写公司'} · ${item.role_title || '未填写岗位'}`;
    const meta = document.createElement('span');
    meta.className = 'record-meta';
    meta.textContent = `${item.status || 'draft'} · ${item.updated_at || ''}`;
    li.append(title, meta);
    li.addEventListener('click', () => activateProject(item));
    list.appendChild(li);
  }
  renderResumeCards();
}

function activateProject(project) {
  state.activeProject = project;
  $('companyName').value = project.company_name || '';
  $('projectRole').value = project.role_title || '';
  $('targetTitle').value = project.role_title || $('targetTitle').value;
  $('jdText').value = project.jd_text || '';
  $('projectStatus').value = project.status || 'draft';
  $('projectNotes').value = project.notes || '';
  const content = project.resume_content || {};
  if (content.summary) $('summary').value = content.summary;
  if (content.education) $('educationText').value = content.education;
  if (content.work) $('workResumeText').value = content.work;
  if (content.projects) $('projectResumeText').value = content.projects;
  if (content.awards) $('awardResumeText').value = content.awards;
  if (content.skills) $('skills').value = content.skills;
  if (content.other) $('otherResumeText').value = content.other;
  showWorkspaceView('editor');
  $('status').textContent = `正在编辑：${resumeTitle(project)}`;
}

function renderResumeCards() {
  const grid = $('resumeCardGrid');
  if (!grid) return;
  grid.querySelectorAll('.resume-card:not(.create-card)').forEach((card) => card.remove());
  for (const project of state.projects) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'resume-card';
    const icon = document.createElement('span');
    icon.className = 'resume-card-icon';
    icon.textContent = 'FO';
    const menu = document.createElement('span');
    menu.className = 'resume-card-menu';
    menu.textContent = '⋮';
    const title = document.createElement('strong');
    title.textContent = resumeTitle(project);
    const meta = document.createElement('span');
    meta.textContent = `${project.updated_at || '刚刚'} · ${project.status || 'draft'}`;
    card.append(icon, menu, title, meta);
    card.addEventListener('click', () => activateProject(project));
    grid.appendChild(card);
  }
}

function setSourceCategory(category) {
  state.sourceCategory = normalizeCategory(category);
  document.querySelectorAll('[data-source-category]').forEach((button) => {
    button.classList.toggle('active', normalizeCategory(button.dataset.sourceCategory) === state.sourceCategory);
  });
  renderExperiences();
}

function formatExperienceForResume(item) {
  const lines = [];
  const heading = [item.title, item.organization].filter(Boolean).join('｜') || '未命名经历';
  lines.push(heading);
  for (const bullet of item.bullets || []) lines.push(`- ${bullet}`);
  for (const metric of item.metrics || []) lines.push(`- 结果：${metric}`);
  if ((item.skills || []).length) lines.push(`- 关键词：${item.skills.join('、')}`);
  return lines.join('\n');
}

function insertExperienceToResume(item) {
  const category = normalizeCategory(item.category);
  const targetId = resumeSectionTargets[category] || 'workResumeText';
  const target = $(targetId);
  const incoming = formatExperienceForResume(item);
  if (!target) return;
  const current = target.value.trim();
  target.value = current && !current.startsWith('待') ? `${current}\n\n${incoming}` : incoming;
  $('status').textContent = `已插入到${categoryLabels[category] || '简历'}`;
}

function openExperienceDialog(category = state.sourceCategory) {
  renderExperienceTemplate(category);
  $('experienceTypeStep').hidden = false;
  $('experienceFormStep').hidden = true;
  $('experienceDialog').showModal();
}

function showExperienceForm(category) {
  renderExperienceTemplate(category);
  $('experienceTypeStep').hidden = true;
  $('experienceFormStep').hidden = false;
}

function renderExperienceTemplate(category) {
  const normalized = normalizeCategory(category);
  const template = experienceTemplates[normalized] || experienceTemplates.work;
  $('experienceCategory').value = normalized;
  $('experienceTemplateTitle').textContent = template.title;
  $('experienceTemplateHint').textContent = template.hint;
  const target = $('experienceTemplateFields');
  target.innerHTML = '';
  template.fields.forEach(([key, label, type, placeholder]) => {
    const fieldLabel = document.createElement('label');
    fieldLabel.textContent = label;
    const field = document.createElement(type === 'textarea' ? 'textarea' : 'input');
    field.dataset.templateField = key;
    field.placeholder = placeholder || '';
    if (type === 'textarea') field.className = 'template-textarea';
    fieldLabel.appendChild(field);
    target.appendChild(fieldLabel);
  });
  renderTemplateGuide();
  hydrateTemplateDefaults(normalized);
}

function renderTemplateGuide() {
  const target = $('experienceTemplateGuide');
  target.innerHTML = '';
  const questionBlock = document.createElement('section');
  const questionTitle = document.createElement('h4');
  questionTitle.textContent = '采集追问';
  const questionList = document.createElement('div');
  questionList.className = 'guide-chip-list';
  universalExperienceQuestions.forEach((question) => {
    const chip = document.createElement('span');
    chip.textContent = question;
    questionList.appendChild(chip);
  });
  questionBlock.append(questionTitle, questionList);
  const formulaBlock = document.createElement('section');
  const formulaTitle = document.createElement('h4');
  formulaTitle.textContent = '简历 bullet 句式';
  const formulaList = document.createElement('ul');
  bulletFormulaHints.forEach((formula) => {
    const item = document.createElement('li');
    item.textContent = formula;
    formulaList.appendChild(item);
  });
  formulaBlock.append(formulaTitle, formulaList);
  target.append(questionBlock, formulaBlock);
}

function hydrateTemplateDefaults(category) {
  const defaults = {
    basic: {
      legal_name: $('name').value,
      target_role: $('targetTitle').value,
      city: $('location').value,
      email: $('email').value,
      phone: $('phone').value,
      core_strengths: $('skills').value,
      summary_positioning: $('summary').value
    },
    work: {
      role: $('targetTitle').value
    },
    project: {
      project_role: $('targetTitle').value
    }
  };
  const values = defaults[category] || {};
  document.querySelectorAll('[data-template-field]').forEach((field) => {
    if (values[field.dataset.templateField]) field.value = values[field.dataset.templateField];
  });
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${basePath}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || '请求失败');
  return data;
}

function fillIfEmpty(id, value) {
  if (value === undefined || value === null) return;
  const target = $(id);
  if (!target || target.value.trim()) return;
  target.value = Array.isArray(value) ? value.join('\n') : String(value);
}

function fillListField(id, value) {
  if (!value || (Array.isArray(value) && value.length === 0)) return;
  const target = $(id);
  const incoming = Array.isArray(value) ? value.join('\n') : String(value);
  if (!target.value.trim()) {
    target.value = incoming;
  }
}

function mergeListField(id, value) {
  const target = $(id);
  const existing = target.value.split('\n').map((line) => line.trim()).filter(Boolean);
  const incoming = Array.isArray(value) ? value : String(value || '').split('\n');
  const merged = [...existing];
  incoming.map((item) => String(item).trim()).filter(Boolean).forEach((item) => {
    if (!merged.includes(item)) merged.push(item);
  });
  target.value = merged.join('\n');
}

function renderAiResult(ai) {
  $('aiReply').textContent = ai.reply || ai.authenticity_notice || '已完成';
  renderSkillChips(ai.selected_skills || []);
  renderList('aiSuggestions', ai.suggestions || [], '无');
  renderList('aiQuestions', ai.questions || ai.missing_information || [], '无');
  renderList('aiWarnings', ai.evidence_warnings || [ai.authenticity_notice].filter(Boolean), '无');
  $('aiStatus').textContent = ai.confidence ? `置信度：${ai.confidence}` : '已完成';
}

function renderSkillChips(skills) {
  const target = $('aiSkills');
  target.innerHTML = '';
  if (!skills || skills.length === 0) {
    target.textContent = '未匹配';
    return;
  }
  for (const skill of skills) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = skill.name || skill.skill_id;
    target.appendChild(chip);
  }
}

async function aiAutofill(target) {
  $('aiStatus').textContent = 'AI 分析中';
  try {
    const data = await requestJson('/api/ai/autofill', {
      method: 'POST',
      body: JSON.stringify({ target, context: workspaceContext() })
    });
    const fields = data.ai.suggested_fields || {};
    if (target === 'experience') {
      fillListField('experienceBullets', fields.bullets);
      fillListField('experienceMetrics', fields.metrics);
      fillIfEmpty('experienceSkills', fields.skills);
    } else {
      fillIfEmpty('projectRole', fields.role_title);
      fillIfEmpty('jdText', fields.jd_text);
      fillIfEmpty('projectNotes', fields.notes);
    }
    renderAiResult(data.ai);
    $('status').textContent = 'AI 补全完成';
  } catch (error) {
    $('status').textContent = error.message;
  }
}

function renderExperienceAiDraft(ai) {
  const draft = $('experienceAiDraft');
  const bullets = (ai.polished_bullets || []).filter(Boolean);
  state.experienceAiDraft = bullets;
  $('experienceAiSummary').textContent = ai.summary || '请核对这份建议稿是否准确反映你的真实经历。';
  $('experienceAiNotice').textContent = ai.authenticity_notice || '';
  const list = $('experienceAiBullets');
  list.innerHTML = '';
  for (const bullet of bullets) {
    const item = document.createElement('li');
    item.textContent = bullet;
    list.appendChild(item);
  }
  if (!bullets.length) {
    const item = document.createElement('li');
    item.textContent = '信息还不足以生成建议稿，请先回答 AI 的追问。';
    list.appendChild(item);
  }
  draft.hidden = false;
  renderAiResult({
    reply: ai.summary,
    questions: ai.questions,
    evidence_warnings: ai.evidence_warnings,
    authenticity_notice: ai.authenticity_notice,
    confidence: ai.requires_confirmation ? '待用户确认' : '已完成'
  });
}

async function aiExtractExperience() {
  $('status').textContent = 'AI 正在提取已填事实';
  try {
    const data = await requestJson('/api/ai/autofill', {
      method: 'POST',
      body: JSON.stringify({ target: 'experience', context: workspaceContext() })
    });
    const fields = data.ai.suggested_fields || {};
    mergeListField('experienceBullets', fields.bullets);
    mergeListField('experienceMetrics', fields.metrics);
    if (!$('experienceSkills').value.trim() && fields.skills) {
      $('experienceSkills').value = Array.isArray(fields.skills) ? fields.skills.join(', ') : String(fields.skills);
    }
    renderAiResult(data.ai);
    $('status').textContent = '已提取现有事实，未新增任何经历信息';
  } catch (error) {
    $('status').textContent = error.message;
  }
}

async function aiPolishExperience() {
  $('aiPolishExperienceBtn').disabled = true;
  $('status').textContent = 'AI 正在生成待确认润色稿';
  try {
    const data = await requestJson('/api/ai/polish-experience', {
      method: 'POST',
      body: JSON.stringify({ context: workspaceContext() })
    });
    renderExperienceAiDraft(data.ai);
    $('status').textContent = data.ai.polished_bullets.length ? '润色建议稿已生成，请核对后采纳' : 'AI 需要更多真实素材';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    $('aiPolishExperienceBtn').disabled = false;
  }
}

function applyExperienceAiDraft() {
  if (!state.experienceAiDraft.length) return;
  $('experienceBullets').value = state.experienceAiDraft.join('\n');
  $('experienceAiDraft').hidden = true;
  $('status').textContent = '已采纳建议稿。保存前请再次确认每条均为真实事实。';
}

async function aiReview() {
  $('aiStatus').textContent = 'AI 分析中';
  $('aiReply').textContent = '';
  try {
    const response = await fetch(`${basePath}/api/ai/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: $('aiMessage').value, context: workspaceContext() })
    });
    if (!response.ok || !response.body) {
      throw new Error('stream_unavailable');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalAi = null;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === 'delta') {
          $('aiReply').textContent += event.text || '';
        }
        if (event.type === 'final') {
          finalAi = event.ai;
        }
      }
    }
    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      if (event.type === 'delta') $('aiReply').textContent += event.text || '';
      if (event.type === 'final') finalAi = event.ai;
    }
    if (finalAi) {
      renderAiResult({ ...finalAi, reply: $('aiReply').textContent || finalAi.reply });
    }
    $('status').textContent = 'AI 建议已生成';
  } catch (error) {
    try {
      const data = await requestJson('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message: $('aiMessage').value, context: workspaceContext() })
      });
      renderAiResult(data.ai);
      $('status').textContent = 'AI 建议已生成';
    } catch (fallbackError) {
      $('status').textContent = fallbackError.message || error.message;
    }
  }
}

async function saveExperience() {
  requireUser();
  const button = $('saveExperienceBtn');
  button.disabled = true;
  $('status').textContent = '保存经历中';
  try {
    const data = await requestJson(`/api/users/${encodeURIComponent(activeUserId())}/experiences`, {
      method: 'POST',
      body: JSON.stringify(currentExperiencePayload())
    });
    $('userId').value = data.experience.user_id;
    $('savedUser').textContent = data.experience.user_id;
    await loadUserWorkspace(data.experience.user_id);
    setSourceCategory($('experienceCategory').value);
    if ($('experienceDialog').open) $('experienceDialog').close();
    $('status').textContent = '经历已保存';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function saveProject() {
  requireUser();
  const button = $('saveProjectBtn');
  button.disabled = true;
  $('status').textContent = '保存项目中';
  try {
    const data = await requestJson(`/api/users/${encodeURIComponent(activeUserId())}/projects`, {
      method: 'POST',
      body: JSON.stringify(currentProjectPayload())
    });
    $('userId').value = data.project.user_id;
    $('savedUser').textContent = data.project.user_id;
    await loadUserWorkspace(data.project.user_id);
    activateProject(data.project);
    $('status').textContent = '项目已保存';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function loadUserWorkspace(userId = activeUserId()) {
  if (!userId) return;
  try {
    const [experienceData, projectData, historyData] = await Promise.all([
      requestJson(`/api/users/${encodeURIComponent(userId)}/experiences`),
      requestJson(`/api/users/${encodeURIComponent(userId)}/projects`),
      fetch(`${basePath}/api/users/${encodeURIComponent(userId)}/generations`).then((response) => response.ok ? response.json() : { generations: [] })
    ]);
    state.experiences = experienceData.experiences || [];
    state.projects = projectData.projects || [];
    $('userId').value = userId;
    $('savedUser').textContent = userId;
    renderExperiences();
    renderProjects();
    renderHistory(historyData.generations || []);
    $('status').textContent = '已读取';
  } catch (error) {
    $('status').textContent = error.message;
  }
}

async function generate() {
  requireUser();
  const button = $('generateBtn');
  button.disabled = true;
  $('status').textContent = '生成中';
  try {
    const data = await requestJson('/api/generate', {
      method: 'POST',
      body: JSON.stringify({
        user_id: activeUserId(),
        profile: profilePayload(),
        jd_text: $('jdText').value,
        target_role: $('projectRole').value || $('targetTitle').value
      })
    });
    $('contentScore').textContent = data.content ? data.content.score : '--';
    $('score').textContent = data.ats.score;
    $('resumePreview').textContent = data.resume_markdown;
    $('savedUser').textContent = data.persistence.user_id;
    $('userId').value = data.persistence.user_id;
    renderList('missing', data.ats.missing_keywords, '无');
    renderList('warnings', data.ats.warnings, '无');
    renderList('contentGaps', data.content ? data.content.content_gaps : [], '无');
    await loadUserWorkspace(data.persistence.user_id);
    $('status').textContent = '已生成';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function renderHistory(generations) {
  const target = $('history');
  target.innerHTML = '';
  for (const item of generations.slice(0, 5)) {
    const li = document.createElement('li');
    const score = item.ats_report && item.ats_report.score !== undefined ? item.ats_report.score : '--';
    li.textContent = `${item.created_at} · ${item.target_role || '目标岗位'} · ATS ${score}`;
    target.appendChild(li);
  }
}

$('saveExperienceBtn').addEventListener('click', saveExperience);
$('saveProjectBtn').addEventListener('click', saveProject);
$('loadUserBtn').addEventListener('click', () => loadUserWorkspace());
$('generateBtn').addEventListener('click', generate);
$('createResumeBtn').addEventListener('click', createNewResume);
$('topCreateResumeBtn').addEventListener('click', createNewResume);
$('newResumeCard').addEventListener('click', createNewResume);
$('submitNewResumeBtn').addEventListener('click', submitNewResume);
$('closeNewResumeDialogBtn').addEventListener('click', () => $('newResumeDialog').close());
$('cancelNewResumeBtn').addEventListener('click', () => $('newResumeDialog').close());
$('closeVersionHistoryDialogBtn').addEventListener('click', () => $('versionHistoryDialog').close());
$('addExperienceBtn').addEventListener('click', () => openExperienceDialog());
$('topAddExperienceBtn').addEventListener('click', () => openExperienceDialog());
$('versionHistoryBtn').addEventListener('click', openVersionHistory);
$('exportBtn').addEventListener('click', () => {
  generate();
});
$('closeExperienceDialogBtn').addEventListener('click', () => $('experienceDialog').close());
$('backExperienceTypesBtn').addEventListener('click', () => {
  $('experienceTypeStep').hidden = false;
  $('experienceFormStep').hidden = true;
});
$('experienceCategory').addEventListener('change', () => renderExperienceTemplate($('experienceCategory').value));
$('aiFilterBtn').addEventListener('click', () => {
  for (const item of state.experiences) insertExperienceToResume(item);
});
$('aiExperienceBtn').addEventListener('click', () => aiAutofill('experience'));
$('aiExtractExperienceBtn').addEventListener('click', aiExtractExperience);
$('aiPolishExperienceBtn').addEventListener('click', aiPolishExperience);
$('applyExperienceAiDraftBtn').addEventListener('click', applyExperienceAiDraft);
$('aiProjectBtn').addEventListener('click', () => aiAutofill('project'));
$('aiReviewBtn').addEventListener('click', aiReview);
$('showLoginBtn').addEventListener('click', () => setAuthMode('login'));
$('showRegisterBtn').addEventListener('click', () => setAuthMode('register'));
$('testLoginBtn').addEventListener('click', loginTestAccount);
$('loginForm').addEventListener('submit', login);
$('registerForm').addEventListener('submit', register);
$('logoutBtn').addEventListener('click', logout);
$('resetTestAccountBtn').addEventListener('click', resetTestAccount);
$('userBadge').addEventListener('click', openUserExperiences);
document.querySelectorAll('[data-source-category]').forEach((button) => {
  button.addEventListener('click', () => setSourceCategory(button.dataset.sourceCategory));
});
document.querySelectorAll('[data-dialog-category]').forEach((button) => {
  button.addEventListener('click', () => showExperienceForm(button.dataset.dialogCategory));
});
showWorkspaceView('library');
renderExperiences();
renderProjects();
restoreSession();
