/* SLOY: podpowiedź danych firmy po wpisaniu NIP w koszyku (Biała lista podatników VAT, MF) */
(function(){
  var timer,last='';
  function valid(n){
    if(!/^\d{10}$/.test(n))return false;
    var w=[6,5,7,2,3,4,5,6,7],s=0;
    for(var i=0;i<9;i++)s+=w[i]*+n.charAt(i);
    return s%11===+n.charAt(9);
  }
  function isNip(inp){
    var lab=inp.closest&&inp.closest('label.field');
    var sp=lab&&lab.querySelector('span');
    return sp&&sp.textContent.trim()==='NIP'?lab:null;
  }
  function info(lab){
    var b=lab.querySelector('.nip-info');
    if(!b){b=document.createElement('span');b.className='nip-info';b.setAttribute('aria-live','polite');lab.appendChild(b);}
    return b;
  }
  function say(b,txt,cls){b.textContent=txt;b.className='nip-info'+(cls?' '+cls:'');}
  document.addEventListener('input',function(e){
    var inp=e.target,lab=inp&&inp.tagName==='INPUT'&&isNip(inp);
    if(!lab)return;
    var n=inp.value.replace(/\D/g,''),b=info(lab);
    clearTimeout(timer);
    if(n.length<10){say(b,'');last='';return;}
    if(!valid(n)){say(b,'Ten NIP wygląda na błędny. Sprawdź cyfry.','is-err');last='';return;}
    if(n===last)return;
    say(b,'Sprawdzamy dane firmy…');
    timer=setTimeout(function(){
      last=n;
      var d=new Date().toISOString().slice(0,10);
      fetch('https://wl-api.mf.gov.pl/api/search/nip/'+n+'?date='+d)
        .then(function(r){return r.json();})
        .then(function(j){
          if(inp.value.replace(/\D/g,'')!==n)return;
          var s=j&&j.result&&j.result.subject;
          if(!s){say(b,'Nie znaleźliśmy firmy z tym NIP w rejestrze VAT. Sprawdź numer.','is-err');return;}
          var addr=s.workingAddress||s.residenceAddress||'';
          b.textContent='';b.className='nip-info is-ok';
          var st=document.createElement('strong');st.textContent=s.name;b.appendChild(st);
          if(addr)b.appendChild(document.createTextNode(addr));
          try{sessionStorage.setItem('sloy-nip',JSON.stringify({nip:n,name:s.name,address:addr}));}catch(_){}
        })
        .catch(function(){last='';say(b,'Nie udało się teraz pobrać danych firmy. Możesz kontynuować, sprawdzimy NIP przy fakturze.');});
    },300);
  });
})();
