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

// Ce que l'on regardait dans Cocktails (filtres, lieu choisi, carte ou liste, zoom de la carte) : gardé quand on ouvre
// un cocktail puis qu'on revient (« Retour »), et jusqu'au rechargement de la page.
export const vues = $state({
  liste: { livre: '', base: '', quoi: 'tout', favoris: false },
  lieux: { sorte: 'les-deux', carte: false, choisi: null, zoom: null },
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

// ---------------------------------------------------------------- verres ou litres
// Volume, en cl, des unités du livre (les quantités sont déjà converties en cl à la lecture : ml, oz…).
// Les lignes sans quantité (« compléter avec du soda ») ne comptent pas : le volume d'un verre est celui des
// ingrédients mesurés, avant la glace.
const CL_PAR_UNITE = { cl: 1, shot: 3, 'cuillère à soupe': 1.5, 'cuillère à café': 0.5, 'cuillère de bar': 0.5, cuillère: 0.5,
                       trait: 0.1, goutte: 0.005, pinte: 50, tasse: 25 }

export function volumeVerre(lignes) {
  return lignes.reduce((s, l) => s + (l.quantite != null && !l.facultatif && CL_PAR_UNITE[l.unite] ? l.quantite * CL_PAR_UNITE[l.unite] : 0), 0)
}

const nombre = (v) => String(Math.round(v * 100) / 100).replace('.', ',')

// Quantité d'une ligne pour un facteur (2 verres → 2 ; 1,5 litre d'un verre de 12 cl → 12,5).
// Au-delà d'un litre, les cl passent en litres ; ce qui se compte (feuilles, zestes, œufs) s'arrondit au demi.
export function dose(l, facteur = 1) {
  if (l.quantite == null) return ''
  const v = l.quantite * facteur
  if (l.unite === 'cl') return v >= 100 ? `${nombre(v / 100)} l` : `${nombre(v)} cl`
  const arrondi = CL_PAR_UNITE[l.unite] || Number.isInteger(facteur) ? v : Math.max(0.5, Math.round(v * 2) / 2)
  return `${nombre(arrondi)} ${l.unite}`.trim()
}

// « Évoque le Mexique » : noms des lieux d'une recette
export function nomsLieux(ids) {
  return ids.map((i) => etat.lieux.get(i)?.nom).filter(Boolean).join(', ')
}
