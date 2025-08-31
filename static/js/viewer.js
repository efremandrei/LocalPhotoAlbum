(function(){
  const prevBtn = document.getElementById('nav-prev');
  const nextBtn = document.getElementById('nav-next');
  const titleInput = document.getElementById('photo-title');
  const descInput = document.getElementById('photo-description');
  const saveStatus = document.getElementById('save-status');

  function __getPhotoId(){ return parseInt(document.body.dataset.photoId||"0",10); }
  function go(href){ if(href){ window.location.href = href; } }

  async function saveNow(fields){
    try{
      const pid = __getPhotoId();
      if(!pid) return;
      saveStatus && (saveStatus.textContent = 'Saving...');
      const res = await fetch(`/api/photos/${pid}`, {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(fields),
        keepalive: true
      });
      if(!res.ok) throw new Error('Save failed');
      await res.json();
      saveStatus && (saveStatus.textContent = 'Saved');
      setTimeout(()=>{ if(saveStatus) saveStatus.textContent=''; }, 800);
      __dirtyChanges = false;
    }catch(e){
      console.error(e);
      saveStatus && (saveStatus.textContent = 'Error');
    }
  }

  let __dirtyChanges = false;
  const deb = (fn, d=500)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), d); }; };
  const debSaveTitle = deb(()=>{ __dirtyChanges = true; saveNow({user_title: titleInput.value}); }, 500);
  const debSaveDesc  = deb(()=>{ __dirtyChanges = true; saveNow({user_description: descInput.value}); }, 600);
  titleInput && titleInput.addEventListener('input', debSaveTitle);
  descInput && descInput.addEventListener('input', debSaveDesc);
  titleInput && titleInput.addEventListener('blur', ()=>{ __dirtyChanges = true; saveNow({user_title: titleInput.value}); });
  descInput && descInput.addEventListener('blur', ()=>{ __dirtyChanges = true; saveNow({user_description: descInput.value}); });

  async function goAfterFlush(href){
    if(__dirtyChanges){
      const fields = {};
      if(titleInput) fields.user_title = titleInput.value;
      if(descInput)  fields.user_description = descInput.value;
      await saveNow(fields);
    }
    go(href);
  }

  prevBtn && prevBtn.addEventListener('click', (e)=>{ e.preventDefault(); goAfterFlush(prevBtn.dataset.href); });
  nextBtn && nextBtn.addEventListener('click', (e)=>{ e.preventDefault(); goAfterFlush(nextBtn.dataset.href); });

  document.addEventListener('keydown', (e)=>{
    if(e.key === 'ArrowLeft' && prevBtn){ e.preventDefault(); goAfterFlush(prevBtn.dataset.href); }
    if(e.key === 'ArrowRight' && nextBtn){ e.preventDefault(); goAfterFlush(nextBtn.dataset.href); }
  });

  // Explicit SAVE button
  const saveBtn = document.getElementById('save-btn');
  saveBtn && saveBtn.addEventListener('click', ()=>{
    const fields = {
      user_title: titleInput ? titleInput.value : null,
      user_description: descInput ? descInput.value : null
    };
    __dirtyChanges = false;
    saveNow(fields);
  });
})();

/* --- Zoom / Pan --- */
(function(){
  const img = document.querySelector('.viewer-img');
  if(!img) return;
  const zoomInBtn = document.getElementById('zoom-in');
  const zoomOutBtn = document.getElementById('zoom-out');
  const zoomResetBtn = document.getElementById('zoom-reset');
  const zoomLevel = document.getElementById('zoom-level');

  let scale = 1, minScale = 0.5, maxScale = 4;
  let pos = {x: 0, y: 0};
  let dragging = false;
  let start = {x: 0, y: 0};

  function clamp(v, lo, hi){ return Math.max(lo, Math.min(hi, v)); }
  function apply(){
    img.style.transformOrigin = 'center center';
    img.style.transform = `translate(${pos.x}px, ${pos.y}px) scale(${scale})`;
    if(zoomLevel){ zoomLevel.textContent = Math.round(scale * 100) + '%'; }
  }

  zoomInBtn?.addEventListener('click', ()=>{ scale = clamp(scale+0.2, minScale, maxScale); apply(); });
  zoomOutBtn?.addEventListener('click', ()=>{ scale = clamp(scale-0.2, minScale, maxScale); apply(); });
  zoomResetBtn?.addEventListener('click', ()=>{ scale = 1; pos={x:0,y:0}; apply(); });
  img.addEventListener('dblclick', ()=>{ scale = 1; pos={x:0,y:0}; apply(); });

  img.addEventListener('wheel', (e)=>{
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.1 : -0.1;
    scale = clamp(scale + delta, minScale, maxScale);
    apply();
  }, {passive:false});

  img.addEventListener('mousedown', (e)=>{
    dragging = true;
    img.classList.add('dragging');
    start.x = e.clientX - pos.x;
    start.y = e.clientY - pos.y;
  });
  window.addEventListener('mousemove', (e)=>{
    if(!dragging) return;
    pos.x = e.clientX - start.x;
    pos.y = e.clientY - start.y;
    apply();
  });
  window.addEventListener('mouseup', ()=>{
    if(dragging){
      dragging = false;
      img.classList.remove('dragging');
    }
  });

  apply();
})();
