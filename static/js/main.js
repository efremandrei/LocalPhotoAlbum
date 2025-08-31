// Simple helper for JSON fetch
async function postJSON(url, payload, method='POST'){
  const res = await fetch(url, {
    method: method,
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(!res.ok){ throw new Error(await res.text()); }
  return await res.json();
}

function debounce(fn, delay=400){
  let t=null;
  return (...args)=>{
    clearTimeout(t);
    t=setTimeout(()=>fn(...args), delay);
  }
}
