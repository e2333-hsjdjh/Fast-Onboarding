const basePath = document.querySelector('script[src$="app.js"]').getAttribute('src').replace(/\/static\/app\.js$/, '');

const $ = (id) => document.getElementById(id);

function linesToExperience(text) {
  const lines = text.split('\n').map((line) => line.trim()).filter(Boolean);
  const [titleLine = '项目经历 | 待补充', ...rest] = lines;
  const [title, organization = ''] = titleLine.split('|').map((part) => part.trim());
  const metrics = rest.filter((line) => line.startsWith('量化结果')).map((line) => line.replace(/^量化结果[:：]/, '').trim());
  const bullets = rest.filter((line) => !line.startsWith('量化结果'));
  return { title, organization, bullets, metrics, skills: [] };
}

function profilePayload() {
  return {
    name: $('name').value,
    target_title: $('targetTitle').value,
    email: $('email').value,
    phone: $('phone').value,
    location: $('location').value,
    summary: $('summary').value,
    skills: $('skills').value.split(/[,，、\n]/).map((item) => item.trim()).filter(Boolean),
    experiences: [linesToExperience($('experienceText').value)],
    projects: [linesToExperience($('projectText').value)],
    education: ['待补充']
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

async function generate() {
  const button = $('generateBtn');
  button.disabled = true;
  $('status').textContent = '生成中';
  try {
    const response = await fetch(`${basePath}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: $('userId').value,
        profile: profilePayload(),
        jd_text: $('jdText').value,
        target_role: $('targetTitle').value
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error || '生成失败');
    $('score').textContent = data.ats.score;
    $('resumePreview').textContent = data.resume_markdown;
    $('savedUser').textContent = data.persistence.user_id;
    $('userId').value = data.persistence.user_id;
    renderList('missing', data.ats.missing_keywords, '无');
    renderList('warnings', data.ats.warnings, '无');
    await loadHistory(data.persistence.user_id);
    $('status').textContent = '已生成';
  } catch (error) {
    $('status').textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function loadHistory(userId) {
  if (!userId) return;
  const response = await fetch(`${basePath}/api/users/${encodeURIComponent(userId)}/generations`);
  if (!response.ok) return;
  const data = await response.json();
  const target = $('history');
  target.innerHTML = '';
  for (const item of data.generations.slice(0, 5)) {
    const li = document.createElement('li');
    const score = item.ats_report && item.ats_report.score !== undefined ? item.ats_report.score : '--';
    li.textContent = `${item.created_at} · ${item.target_role || '目标岗位'} · ATS ${score}`;
    target.appendChild(li);
  }
}

$('generateBtn').addEventListener('click', generate);
