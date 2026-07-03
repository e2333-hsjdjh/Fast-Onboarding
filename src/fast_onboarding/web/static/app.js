const basePath = document.querySelector('script[src$="app.js"]').getAttribute('src').replace(/\/static\/app\.js$/, '');

const $ = (id) => document.getElementById(id);
const state = {
  experiences: [],
  projects: [],
  page: 'overview'
};

function splitValues(text) {
  return text.split(/[,，、\n]/).map((item) => item.trim()).filter(Boolean);
}

function showPage(pageName) {
  const next = pageName || 'overview';
  state.page = next;
  document.querySelectorAll('[data-page]').forEach((page) => {
    page.classList.toggle('active', page.dataset.page === next);
  });
  document.querySelectorAll('[data-page-link]').forEach((link) => {
    link.classList.toggle('active', link.dataset.pageLink === next);
  });
}

function activeUserId() {
  return ($('userId').value || $('email').value || $('phone').value || $('name').value || 'local-user').trim().toLowerCase().replace(/\s+/g, '-');
}

function currentExperiencePayload() {
  return {
    user_name: $('name').value,
    category: $('experienceCategory').value,
    title: $('experienceTitle').value,
    organization: $('experienceOrg').value,
    bullets: $('experienceBullets').value.split('\n').map((line) => line.trim()).filter(Boolean),
    metrics: $('experienceMetrics').value.split('\n').map((line) => line.trim()).filter(Boolean),
    skills: splitValues($('experienceSkills').value)
  };
}

function currentProjectPayload() {
  return {
    user_name: $('name').value,
    company_name: $('companyName').value,
    role_title: $('projectRole').value,
    jd_text: $('jdText').value,
    status: $('projectStatus').value,
    notes: $('projectNotes').value
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
  const experiences = saved.filter((item) => item.category !== 'project').map(toResumeExperience);
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
    education: ['待补充']
  };
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
  for (const item of state.experiences) {
    const li = document.createElement('li');
    const title = document.createElement('strong');
    title.textContent = item.title || '未命名经历';
    const meta = document.createElement('span');
    meta.className = 'record-meta';
    meta.textContent = `${item.organization || '未填写组织'} · ${item.category === 'project' ? '项目' : '经历'} · ${(item.skills || []).join('、') || '无技能标签'}`;
    li.append(title, meta);
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
}

function activateProject(project) {
  $('companyName').value = project.company_name || '';
  $('projectRole').value = project.role_title || '';
  $('targetTitle').value = project.role_title || $('targetTitle').value;
  $('jdText').value = project.jd_text || '';
  $('projectStatus').value = project.status || 'draft';
  $('projectNotes').value = project.notes || '';
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
      showPage('profile');
    } else {
      fillIfEmpty('projectRole', fields.role_title);
      fillIfEmpty('jdText', fields.jd_text);
      fillIfEmpty('projectNotes', fields.notes);
      showPage('projects');
    }
    renderAiResult(data.ai);
    $('status').textContent = 'AI 补全完成';
  } catch (error) {
    $('status').textContent = error.message;
  }
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
    showPage('profile');
    $('status').textContent = '经历已保存';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function saveProject() {
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
    showPage('projects');
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
    showPage('results');
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
$('aiExperienceBtn').addEventListener('click', () => aiAutofill('experience'));
$('aiProjectBtn').addEventListener('click', () => aiAutofill('project'));
$('aiReviewBtn').addEventListener('click', aiReview);
document.querySelectorAll('[data-page-link]').forEach((link) => {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    showPage(link.dataset.pageLink);
    document.getElementById('workspace').scrollIntoView({ block: 'start' });
  });
});

showPage('overview');
renderExperiences();
renderProjects();
