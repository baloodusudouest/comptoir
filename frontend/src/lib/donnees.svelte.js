// Données partagées entre les écrans : la liste des recettes et le calcul du bar, relus après chaque changement.
import { api } from './api.js'

export const etat = $state({
  recettes: [],
  faisables: new Set(),
  presque: new Map(), // id → manquants
  debloque: [],
  bases: [],
  aTraiter: 0,
  lieux: new Map(), // id → lieu (nom, chemin, type, iso, lat, lon, cree_a, evoque)
  charge: false,
})

export async function recharger() {
  const [d, t, l] = await Promise.all([api.get('/api/recettes'), api.get('/api/a-traiter'), api.get('/api/lieux')])
  etat.recettes = d.recettes
  etat.faisables = new Set(d.faisables)
  etat.presque = new Map(d.presque.map((p) => [p.recette, p.manque]))
  etat.debloque = d.debloque
  etat.bases = d.bases
  etat.aTraiter = t.tuiles.reduce((s, x) => s + x.nombre, 0)
  etat.lieux = new Map(l.map((x) => [x.id, x]))
  etat.charge = true
}

// « Mon livre, p. 42-43 » ; le livre seul si la page n'est pas connue
export function source(r) {
  return r.pages ? `${r.livre}, ${r.pages}` : r.livre
}

export function quantite(q, verres = 1) {
  if (q == null) return ''
  const v = Math.round(q * verres * 100) / 100
  return String(v).replace('.', ',')
}

// « Évoque le Mexique » : noms des lieux d'une recette
export function nomsLieux(ids) {
  return ids.map((i) => etat.lieux.get(i)?.nom).filter(Boolean).join(', ')
}
