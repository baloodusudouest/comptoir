// Appels à l'API de Comptoir. Une réponse 401 renvoie à l'écran de connexion.
export class ErreurApi extends Error {
  constructor(message, statut, donnees) {
    super(message)
    this.statut = statut
    this.donnees = donnees
  }
}

async function appel(methode, chemin, corps, brut = false) {
  const r = await fetch(chemin, {
    method: methode,
    headers: corps && !brut ? { 'Content-Type': 'application/json' } : brut ? { 'Content-Type': 'application/epub+zip' } : undefined,
    body: brut ? corps : corps ? JSON.stringify(corps) : undefined,
    credentials: 'same-origin',
  })
  let donnees = null
  try { donnees = await r.json() } catch { /* réponse sans contenu */ }
  if (r.status === 401 && chemin !== '/api/connexion') window.dispatchEvent(new Event('comptoir-deconnecte'))
  if (!r.ok) throw new ErreurApi(donnees?.detail || `Le serveur a répondu ${r.status}.`, r.status, donnees)
  return donnees
}

export const api = {
  get: (chemin) => appel('GET', chemin),
  post: (chemin, corps) => appel('POST', chemin, corps ?? {}),
  put: (chemin, corps) => appel('PUT', chemin, corps ?? {}),
  del: (chemin) => appel('DELETE', chemin),
  envoyer: (chemin, fichier) => appel('POST', chemin, fichier, true),
}
