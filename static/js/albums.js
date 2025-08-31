// Folder picker logic for Albums page
(function(){
  function $(id){ return document.getElementById(id); }
  function on(el, ev, fn){ el && el.addEventListener(ev, fn); }

  function show(el){ if(el){ el.classList.remove('hidden'); el.style.display='block'; } }
  function hide(el){ if(el){ el.classList.add('hidden'); el.style.display='none'; } }

  async function loadDir(path){
    const url = path ? `/api/fs/list?path=${encodeURIComponent(path)}` : '/api/fs/list';
    const res = await fetch(url);
    if(!res.ok){ alert('Cannot list folder'); return; }
    const data = await res.json();
    const list = $('fs-list');
    const drives = $('fs-drives');
    const fsPath = $('fs-path');
    const btnUp = $('fs-up');

    if(!list || !drives || !fsPath || !btnUp) return;

    fsPath.value = data.cwd || '';
    // Drives
    drives.innerHTML = '';
    if(Array.isArray(data.drives) && data.drives.length){
      for(const d of data.drives){
        const b = document.createElement('button');
        b.className = 'btn';
        b.type = 'button';
        b.textContent = d;
        b.addEventListener('click', ()=> loadDir(d));
        drives.appendChild(b);
      }
    }
    // Dirs
    list.innerHTML = '';
    if(Array.isArray(data.dirs)){
      for(const item of data.dirs){
        const a = document.createElement('button');
        a.className = 'btn';
        a.type = 'button';
        a.style.display = 'block';
        a.textContent = item.name;
        a.title = item.path;
        a.addEventListener('click', ()=> loadDir(item.path));
        list.appendChild(a);
      }
    }
    // Up
    btnUp.onclick = ()=>{
      if(data.parent){ loadDir(data.parent); }
    };
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    const browse = $('btn-browse');
    const modal = $('fs-modal');
    const closeBtn = $('fs-close');
    const go = $('fs-go');
    const fsPath = $('fs-path');
    const select = $('fs-select');
    const inputPath = $('album-path');

    // No modal on non-albums pages
    if(!browse) return;

    on(browse, 'click', (e)=>{
      e.preventDefault();
      show(modal);
      loadDir('');
    });
    on(go, 'click', ()=> loadDir(fsPath.value.trim()));
    on(select, 'click', ()=>{
      if(!fsPath || !inputPath) return;
      inputPath.value = fsPath.value.trim();
      hide(modal);
    });
    // Allow Esc to close
    on(document, 'keydown', (e)=>{
      if(e.key === 'Escape') hide(modal);
    });
    // Clicking backdrop closes
    const backdrop = modal ? modal.querySelector('.modal-backdrop') : null;
    on(backdrop, 'click', ()=> hide(modal));
  });
})();

  // Close button
  closeBtn && closeBtn.addEventListener('click', ()=> hide(modal));


(function(){
  function $(id){ return document.getElementById(id); }
  function on(el, ev, fn){ el && el.addEventListener(ev, fn); }
  function show(el){ if(el){ el.classList.remove('hidden'); el.style.display='block'; } }
  function hide(el){ if(el){ el.classList.add('hidden'); el.style.display='none'; } }

  async function addAlbumAsync(){
    const pathInput = $('album-path');
    const waitModal = $('wait-modal');
    const path = pathInput ? pathInput.value.trim() : '';
    if(!path){ alert('Please choose a folder.'); return; }

    // Try async endpoint first
    try{
      show(waitModal);
      const res = await fetch('/api/albums/add_async', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({path})
      });
      if(!res.ok) throw new Error(await res.text());
      const {task_id} = await res.json();
      if(!task_id) throw new Error('No task id');

      // Poll
      let tries = 0;
      while(true){
        await new Promise(r=> setTimeout(r, 800));
        const st = await fetch(`/api/tasks/${task_id}`);
        if(!st.ok) throw new Error('Task not found');
        const data = await st.json();
        if(data.state === 'done'){
          hide(waitModal);
          alert(`Scanned ${data.photos_scanned} photos for album "${data.album_name}".`);
          window.location.reload();
          return;
        }else if(data.state === 'error'){
          hide(waitModal);
          alert('Error: ' + (data.message || 'Unknown error'));
          return;
        }
        // still pending...
        tries++;
        // (Optional) could add timeout; leaving it open for long scans
      }
    }catch(err){
      console.error(err);
      // Fallback to synchronous endpoint with a wait modal
      try{
        show($('wait-modal'));
        const res2 = await fetch('/api/albums/add', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({path})
        });
        if(!res2.ok){ hide($('wait-modal')); throw new Error(await res2.text()); }
        const data2 = await res2.json();
        hide($('wait-modal'));
        alert('Scanned ' + data2.photos_scanned + ' photos for album "' + data2.album_name + '".');
        window.location.reload();
      }catch(e2){
        hide($('wait-modal'));
        alert('Add failed: ' + e2.message);
      }
    }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    const btnAdd = $('btn-add');
    on(btnAdd, 'click', (e)=>{ e.preventDefault(); addAlbumAsync(); });
  });
})();
