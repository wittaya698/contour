// A shown term's one line, where a page first shows it (ADR 0025, decision 1;
// issue 77). The lines arrive with the page as TAUGHT; which ones the viewer
// has closed is asked of the host once, and a host that cannot say leaves every
// line showing — the record is a convenience, and the page explains without it.
let closedTerms = null;

function teach(term) {
  const p = document.createElement('p');
  p.className = 'teach';
  const word = document.createElement('strong');
  word.textContent = term;
  const shut = document.createElement('button');
  shut.type = 'button';
  shut.className = 'shut';
  shut.textContent = 'Got it';
  shut.addEventListener('click', () => {
    p.hidden = true;
    ask('/taught', { closed: term }).catch(() => {});
  });
  p.append(word, document.createTextNode(' — ' + TAUGHT[term] + ' '), shut);
  closedTerms = closedTerms || ask('/taught').then(r => r.json())
    .then(said => said.closed || []).catch(() => []);
  closedTerms.then(closed => { if (closed.includes(term)) p.hidden = true; });
  return p;
}
