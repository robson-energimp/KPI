const { chromium } = require('playwright');
const OUT = __dirname + '/video';

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1600, height: 900 } },
  });
  const page = await ctx.newPage();
  const wait = (ms) => page.waitForTimeout(ms);

  // ---------- overlay helpers (injected outside Streamlit's React root) ----------
  async function ensureOverlay() {
    await page.evaluate(() => {
      if (document.getElementById('tut-cap')) return;
      const st = document.createElement('style');
      st.textContent = `
        #tut-cap{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);max-width:1100px;
          background:rgba(10,22,40,.92);color:#fff;font:500 24px/1.4 Inter,system-ui,sans-serif;
          padding:16px 28px;border-radius:14px;z-index:999999;box-shadow:0 8px 30px rgba(0,0,0,.35);
          border-left:6px solid #00BCD4;transition:opacity .35s;opacity:0;text-align:left}
        #tut-cap b{color:#4DD0E1}
        #tut-step{position:fixed;top:18px;right:24px;background:#00ACC1;color:#fff;z-index:999999;
          font:700 16px Inter,system-ui,sans-serif;padding:8px 16px;border-radius:999px;opacity:0;transition:opacity .35s}
        #tut-hl{position:fixed;border:4px solid #FFB300;border-radius:14px;z-index:999998;pointer-events:none;
          box-shadow:0 0 0 9999px rgba(0,0,0,.28);transition:all .45s ease;opacity:0}
        #tut-cursor{position:fixed;width:22px;height:22px;border-radius:50%;background:rgba(255,179,0,.85);
          border:3px solid #fff;z-index:1000000;pointer-events:none;transform:translate(-50%,-50%);
          box-shadow:0 2px 8px rgba(0,0,0,.4);left:-50px;top:-50px}
        #tut-cursor.click{animation:tutclick .4s}
        @keyframes tutclick{0%{transform:translate(-50%,-50%) scale(1)}50%{transform:translate(-50%,-50%) scale(1.8)}100%{transform:translate(-50%,-50%) scale(1)}}
        #tut-card{position:fixed;inset:0;z-index:1000001;display:flex;flex-direction:column;align-items:center;
          justify-content:center;background:linear-gradient(135deg,#0D1B3E,#1a3a6e);color:#fff;
          font-family:Inter,system-ui,sans-serif;transition:opacity .6s;text-align:center;padding:40px}
        #tut-card h1{font-size:56px;margin:0 0 18px;font-weight:700}
        #tut-card p{font-size:26px;color:#9fb6d8;margin:6px 0;max-width:1100px;line-height:1.5}
        #tut-card .tag{color:#4DD0E1;font-weight:700;font-size:22px;letter-spacing:.12em;margin-bottom:24px}`;
      document.head.appendChild(st);
      for (const id of ['tut-cap', 'tut-step', 'tut-hl', 'tut-cursor']) {
        const d = document.createElement('div'); d.id = id; document.body.appendChild(d);
      }
      document.addEventListener('mousemove', (e) => {
        const c = document.getElementById('tut-cursor');
        c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      });
    });
  }
  async function caption(html, step) {
    await ensureOverlay();
    await page.evaluate(([h, s]) => {
      const c = document.getElementById('tut-cap');
      c.innerHTML = h; c.style.opacity = h ? 1 : 0;
      if (s !== undefined) { const t = document.getElementById('tut-step'); t.textContent = s; t.style.opacity = s ? 1 : 0; }
    }, [html, step]);
  }
  async function highlight(locator, pad = 8) {
    await ensureOverlay();
    if (!locator) { await page.evaluate(() => (document.getElementById('tut-hl').style.opacity = 0)); return; }
    await locator.scrollIntoViewIfNeeded().catch(() => {});
    const b = await locator.boundingBox();
    if (!b) return;
    await page.evaluate(([b, pad]) => {
      const h = document.getElementById('tut-hl');
      Object.assign(h.style, { left: b.x - pad + 'px', top: b.y - pad + 'px', width: b.width + 2 * pad + 'px', height: b.height + 2 * pad + 'px', opacity: 1 });
    }, [b, pad]);
  }
  async function highlightBox(b, pad = 8) {
    await page.evaluate(([b, pad]) => {
      const h = document.getElementById('tut-hl');
      Object.assign(h.style, { left: b.x - pad + 'px', top: b.y - pad + 'px', width: b.width + 2 * pad + 'px', height: b.height + 2 * pad + 'px', opacity: 1 });
    }, [b, pad]);
  }
  async function moveTo(locator) {
    const b = await locator.boundingBox();
    if (!b) return;
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 25 });
  }
  async function click(locator) {
    await moveTo(locator);
    await page.evaluate(() => { const c = document.getElementById('tut-cursor'); c.classList.remove('click'); void c.offsetWidth; c.classList.add('click'); });
    await wait(250);
    await locator.click();
  }
  async function card(tag, title, lines, ms) {
    await ensureOverlay();
    await page.evaluate(([tag, title, lines]) => {
      let c = document.getElementById('tut-card');
      if (!c) { c = document.createElement('div'); c.id = 'tut-card'; document.body.appendChild(c); }
      c.innerHTML = `<div class="tag">${tag}</div><h1>${title}</h1>` + lines.map((l) => `<p>${l}</p>`).join('');
      c.style.opacity = 1; c.style.display = 'flex';
    }, [tag, title, lines]);
    await wait(ms);
    await page.evaluate(() => { const c = document.getElementById('tut-card'); c.style.opacity = 0; });
    await wait(700);
    await page.evaluate(() => { document.getElementById('tut-card').style.display = 'none'; });
  }
  async function scrollMain(dy, steps = 12) {
    await page.mouse.move(950, 500, { steps: 10 });
    for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await wait(45); }
    await wait(400);
  }
  async function scrollTop() {
    await page.evaluate(() => {
      const m = document.querySelector('[data-testid="stMain"]') || document.querySelector('section.main');
      if (m) m.scrollTo({ top: 0, behavior: 'smooth' });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    await wait(900);
  }
  const tab = (name) => page.getByRole('tab', { name });

  // ---------- roteiro ----------
  await page.goto('http://localhost:8501');
  await page.getByText('Relatório Semanal de Qualidade').first().waitFor();
  await wait(3000);

  await card('TUTORIAL', '⚡ Dashboard KPI Qualidade', [
    'Como usar o painel de acompanhamento semanal da equipe de Qualidade — Energimp',
    'Barra lateral · Painel Principal · Planejamento PCM · Planejamento Semanal · Relatórios',
  ], 5500);

  // 1. Sidebar
  const sidebar = page.locator('section[data-testid="stSidebar"]');
  await caption('A <b>barra lateral</b> controla os dados exibidos em todo o dashboard.', '1 · Barra lateral');
  await highlight(sidebar, 0); await wait(3500);

  const dates = page.getByText('Início', { exact: true }).locator('xpath=ancestor::div[@data-testid="stHorizontalBlock"][1]');
  await caption('Em <b>Período dos Dados</b>, escolha a data de <b>Início</b> e <b>Fim</b>. Todos os KPIs e gráficos são recalculados automaticamente.');
  await highlight(dates); await moveTo(dates); await wait(5000);

  const btnEqm = page.getByRole('button', { name: /Atualizar Dados do EQM/ });
  const btnXls = page.getByRole('button', { name: /Carregar do Excel Local/ });
  await caption('<b>Atualizar Dados do EQM</b> busca os dados direto do banco (modo local). <b>Carregar do Excel Local</b> usa a planilha salva no projeto.');
  const b1 = await btnEqm.boundingBox(), b2 = await btnXls.boundingBox();
  await highlightBox({ x: b1.x, y: b1.y, width: b1.width, height: b2.y + b2.height - b1.y });
  await moveTo(btnEqm); await wait(2500); await moveTo(btnXls); await wait(3000);

  await click(btnXls); await wait(2500);
  await caption('Pronto: os registros do Excel foram carregados. ✅');
  await wait(2500);

  const upl = page.locator('[data-testid="stFileUploader"]').first();
  await upl.scrollIntoViewIfNeeded();
  await caption('No <b>Streamlit Cloud</b>, use <b>Upload de Dados</b> para enviar o arquivo <b>Resumo_Atividades_Qualidade_2026.xlsx</b>.');
  await highlight(upl); await moveTo(upl); await wait(5000);

  const semana = page.getByText(/Semana Atual/).first();
  await semana.scrollIntoViewIfNeeded();
  const sb = await semana.boundingBox();
  await caption('Logo abaixo, o status: <b>semana atual</b>, se os dados estão carregados e quantas atividades estão no <b>PCM</b>.');
  await highlightBox({ x: sb.x - 4, y: sb.y - 4, width: 250, height: 150 }); await moveTo(semana); await wait(5000);
  await highlight(null);

  // 2. Painel principal
  await click(tab(/Painel Principal/)); await wait(800);
  const kpis = page.getByText('ATIVIDADES EM TURBINAS', { exact: false }).first().locator('xpath=ancestor::div[contains(@class,"kpi-grid")][1]');
  await caption('<b>Painel Principal</b>: os 4 cartões mostram os números-chave do período.', '2 · Painel Principal');
  await highlight(kpis); await wait(3500);
  await caption('<b>Atividades em turbinas</b> (turbina + tipo + data), <b>máquinas distintas</b>, <b>ferramentas auditadas</b> e <b>avaliações de equipe</b>.');
  await wait(5000);

  const cob = page.getByText('Cobertura de Máquinas por Regional').first();
  await cob.scrollIntoViewIfNeeded();
  await scrollMain(250);
  const cobGrid = page.getByText('COBERTURA AGD', { exact: false }).first().locator('xpath=ancestor::div[contains(@class,"kpi-grid")][1]');
  await caption('<b>Cobertura por Regional</b> (AGD, BJS, CE): % de turbinas atendidas em relação ao total do parque.');
  await highlight(cobGrid); await wait(5000); await highlight(null);

  const evo = page.getByText('Evolução Semanal').first();
  await evo.scrollIntoViewIfNeeded(); await scrollMain(200);
  await caption('<b>Evolução Semanal</b>: barras = atividades por semana; a linha tracejada é a média do período.');
  await wait(3000); await scrollMain(350); await wait(3500);

  const det = page.getByText('Cobertura Detalhada por Parque').first();
  if (await det.count()) {
    await det.scrollIntoViewIfNeeded(); await scrollMain(150);
    await caption('<b>Cobertura Detalhada por Parque</b>: compare o atendimento de cada parque eólico.');
    await wait(3000); await scrollMain(400); await wait(3000);
  }
  const dsem = page.getByText('Detalhe Semanal').first();
  if (await dsem.count()) {
    await dsem.scrollIntoViewIfNeeded(); await scrollMain(150);
    await caption('<b>Detalhe Semanal</b>: semana anterior e semana atual, com as atividades por regional e turbina.');
    await wait(3000); await scrollMain(450); await wait(3000);
  }
  await scrollTop();

  // 3. Planejamento PCM
  await click(tab(/Planejamento PCM/)); await wait(1200);
  await caption('<b>Planejamento PCM</b>: cadastre as atividades planejadas para a semana.', '3 · Planejamento PCM');
  await wait(3000);
  const form = page.locator('[data-testid="stForm"]').first();
  if (await form.count()) {
    await caption('Preencha <b>Regional</b>, <b>Parque</b>, <b>Tipo de Atividade</b> e demais campos, depois clique em <b>✅ Adicionar Atividade</b>.');
    await highlight(form); await moveTo(form); await wait(6000); await highlight(null);
  }
  const pxe = page.getByText('Planejado × Executado').first();
  if (await pxe.count()) {
    await pxe.scrollIntoViewIfNeeded(); await scrollMain(150);
    await caption('<b>Planejado × Executado</b> cruza o PCM com o que foi realizado (mesmo parque, mesma semana, tipo similar).');
    await wait(5500);
  }
  await scrollTop();

  // 4. Planejamento semanal
  await click(tab(/Planejamento Semanal/)); await wait(1200);
  await caption('<b>Planejamento Semanal</b> tem 3 sub-abas que seguem o fluxo da semana.', '4 · Planejamento Semanal');
  await wait(3500);
  await caption('<b>① Importar Programação</b>: leia os arquivos de programação PCM da pasta local ou faça <b>upload</b> e clique em <b>Criar Tasks de Acompanhamento</b>.');
  const upl2 = page.locator('[data-testid="stFileUploader"]').nth(1);
  if (await upl2.count()) { await highlight(upl2); await moveTo(upl2); }
  await wait(6000); await highlight(null);

  await click(tab(/Acompanhamento Semanal/)); await wait(1500);
  await caption('<b>② Acompanhamento Semanal</b>: escolha a semana, marque as atividades concluídas e informe o <b>motivo</b> quando não forem cumpridas.');
  await wait(4000); await scrollMain(350); await wait(3000); await scrollTop();

  await click(tab(/Relatório \/ Histórico/)); await wait(1500);
  await caption('<b>③ Relatório / Histórico</b>: aderência por regional, motivos de não cumprimento e histórico completo para download.');
  await wait(4000); await scrollMain(400); await wait(3000); await scrollTop();

  // 5. Gerar relatório
  await click(tab(/Gerar Relatório/)); await wait(1500);
  await caption('<b>Gerar Relatório</b>: exporte o relatório corporativo em <b>PDF</b> ou os dados em <b>Excel</b>.', '5 · Relatórios');
  await wait(3500);
  const btnC = page.getByRole('button', { name: /Gerar Completo/ });
  if (await btnC.count()) {
    await caption('<b>Relatório Completo</b>: todas as semanas do período, com capa, KPIs, tabelas, gráficos e resumo acumulado.');
    await highlight(btnC); await moveTo(btnC); await wait(4500);
  }
  const btnA = page.getByRole('button', { name: /Gerar Semana Ant/ });
  if (await btnA.count()) {
    await btnA.scrollIntoViewIfNeeded();
    await caption('<b>Semana Anterior</b>: relatório rápido da última semana, com opção de incluir o PCM da próxima.');
    await highlight(btnA); await wait(3000); await highlight(null);
    await click(btnA);
    await caption('Clique em <b>🚀 Gerar</b> e aguarde…');
    const dl = page.getByRole('button', { name: /Baixar|Download/i }).first();
    await dl.waitFor({ timeout: 90000 }).catch(() => {});
    if (await dl.count()) {
      await dl.scrollIntoViewIfNeeded();
      await caption('Quando o PDF estiver pronto, aparece o botão de <b>download</b>. 📄');
      await highlight(dl); await moveTo(dl); await wait(4500); await highlight(null);
    }
  }
  const exp = page.getByText('Exportar Dados em Excel').first();
  if (await exp.count()) {
    await exp.scrollIntoViewIfNeeded();
    await caption('Em <b>Exportar Dados em Excel</b>, gere a planilha completa do período selecionado.');
    await highlight(exp); await moveTo(exp); await wait(4500); await highlight(null);
  }
  await caption('');

  await card('RESUMO', 'Fluxo semanal recomendado', [
    '1. Defina o período e carregue os dados (EQM, Excel local ou upload)',
    '2. Analise KPIs, cobertura e evolução no Painel Principal',
    '3. Importe a programação PCM e acompanhe as tasks da semana',
    '4. Gere o relatório PDF/Excel e compartilhe com a equipe',
  ], 8000);

  await ctx.close();
  await browser.close();
})();
