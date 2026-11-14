<script>
  // Carte du monde embarquée (world-atlas, 110 m) : rien n'est demandé à Internet.
  // Les pays qui ont des cocktails prennent la couleur de l'appli ; villes et régions sont des points.
  // Zoom : molette et glisser sur PC, pincer et glisser au doigt, double-clic, boutons + / − / Recentrer.
  // Les noms des pays qui ont des cocktails apparaissent à partir du zoom ×2 ; choisir un lieu dans la liste
  // centre la carte sur lui. Traits et points gardent la même épaisseur à tous les zooms.
  import { onMount } from 'svelte'
  import { geoNaturalEarth1, geoPath } from 'd3-geo'
  import { feature } from 'topojson-client'
  import { zoom as d3zoom, zoomIdentity } from 'd3-zoom'
  import { select } from 'd3-selection'
  import 'd3-transition'
  import Plus from '@lucide/svelte/icons/plus'
  import Minus from '@lucide/svelte/icons/minus'
  import Maximize from '@lucide/svelte/icons/maximize-2'
  import monde from 'world-atlas/countries-110m.json'
  import { vues } from '$lib/donnees.svelte.js'

  let { lieux = [], sorte = 'les-deux', choisi = null, onchoisir } = $props()

  const L = 960, H = 500
  const ZOOM_MAX = 12
  const pays = feature(monde, monde.objects.countries).features
  const projection = geoNaturalEarth1().fitSize([L, H], { type: 'Sphere' })
  const chemin = geoPath(projection)
  const formeParIso = new Map(pays.map((p) => [String(p.id), p]))

  const compte = (l) => sorte === 'cree_a' ? l.cree_a.length : sorte === 'evoque' ? l.evoque.length : new Set([...l.cree_a, ...l.evoque]).size
  let parIso = $derived(new Map(lieux.filter((l) => l.type === 'pays' && l.iso && compte(l)).map((l) => [String(l.iso).padStart(3, '0'), l])))
  let points = $derived(lieux.filter((l) => l.type !== 'pays' && compte(l)))
  let maxi = $derived(Math.max(1, ...[...parIso.values()].map(compte)))
  // Étiquettes : au centre de la plus grande partie du pays (la France sans la Guyane, par exemple)
  let etiquettes = $derived([...parIso.entries()].map(([iso, l]) => {
    const f = formeParIso.get(iso)
    return f ? { id: l.id, nom: l.nom, n: compte(l), point: chemin.centroid(plusGrandePartie(f)) } : null
  }).filter((e) => e && Number.isFinite(e.point[0])))

  let svg = $state()
  let t = $state({ k: 1, x: 0, y: 0 })
  let comportement

  function plusGrandePartie(f) {
    if (f.geometry.type !== 'MultiPolygon') return f
    const parties = f.geometry.coordinates.map((c) => ({ type: 'Feature', geometry: { type: 'Polygon', coordinates: c } }))
    return parties.reduce((a, b) => (chemin.area(b) > chemin.area(a) ? b : a))
  }

  function aller(transform, duree = 450) {
    select(svg).transition().duration(matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : duree).call(comportement.transform, transform)
  }
  const zoomer = (facteur) => select(svg).transition().duration(250).call(comportement.scaleBy, facteur)
  const recentrer = () => aller(zoomIdentity)

  function centrerSur(id) {
    const l = lieux.find((x) => x.id === id)
    if (!l) return
    let x, y, k
    const f = l.type === 'pays' && l.iso ? formeParIso.get(String(l.iso).padStart(3, '0')) : null
    if (f) {
      const [[x0, y0], [x1, y1]] = chemin.bounds(plusGrandePartie(f))
      k = Math.min(ZOOM_MAX, 0.8 / Math.max((x1 - x0) / L, (y1 - y0) / H))
      ;[x, y] = [(x0 + x1) / 2, (y0 + y1) / 2]
    } else if (Number.isFinite(l.lon)) {
      ;[x, y] = projection([l.lon, l.lat])
      k = 6
    } else return
    aller(zoomIdentity.translate(L / 2, H / 2).scale(Math.max(k, t.k)).translate(-x, -y))
  }

  let pret = $state(false)
  let dejaCentre = null        // lieu sur lequel la carte est déjà centrée (au retour d'une fiche : ne pas bouger)

  onMount(() => {
    comportement = d3zoom().scaleExtent([1, ZOOM_MAX]).translateExtent([[0, 0], [L, H]])
      .on('zoom', (e) => {
        t = { k: e.transform.k, x: e.transform.x, y: e.transform.y }
        vues.lieux.zoom = { ...t }
      })
    select(svg).call(comportement)
    const z = vues.lieux.zoom
    if (z) {
      select(svg).call(comportement.transform, zoomIdentity.translate(z.x, z.y).scale(z.k))
      dejaCentre = choisi
    }
    pret = true
  })

  // Un lieu choisi dans la liste (ou sur la carte) : la carte va vers lui
  $effect(() => {
    if (pret && choisi && choisi !== dejaCentre) {
      dejaCentre = choisi
      centrerSur(choisi)
    }
  })
</script>

<div class="relative overflow-hidden rounded-xl">
  <svg bind:this={svg} viewBox={`0 0 ${L} ${H}`} class="block w-full cursor-grab touch-none select-none active:cursor-grabbing"
       role="img" aria-label="Carte du monde des cocktails (zoom à la molette, en pinçant, ou avec les boutons)">
    <g transform={`translate(${t.x},${t.y}) scale(${t.k})`}>
      <path d={chemin({ type: 'Sphere' })} fill="var(--card)" />
      {#each pays as p, i (i)}
        {@const l = parIso.get(String(p.id))}
        <path d={chemin(p)} stroke="var(--background)" stroke-width="0.5" vector-effect="non-scaling-stroke"
              fill={l ? 'var(--app)' : 'var(--secondary)'}
              fill-opacity={l ? 0.35 + 0.65 * (compte(l) / maxi) : 1}
              class={l ? 'cursor-pointer' : ''}
              stroke-opacity={l && choisi === l.id ? 1 : 0.8}
              role={l ? 'button' : undefined} tabindex={l ? 0 : undefined} aria-label={l ? `${l.nom} : ${compte(l)}` : undefined}
              onclick={() => l && onchoisir?.(l.id)} onkeydown={(e) => l && e.key === 'Enter' && onchoisir?.(l.id)}>
          {#if l}<title>{l.nom} : {compte(l)}</title>{/if}
        </path>
      {/each}
      {#if t.k >= 2}
        {#each etiquettes as e (e.id)}
          <text x={e.point[0]} y={e.point[1]} font-size={12 / t.k} text-anchor="middle" dominant-baseline="middle"
                fill="var(--foreground)" stroke="var(--background)" stroke-width={3 / t.k} paint-order="stroke"
                class="pointer-events-none" aria-hidden="true">{e.nom}</text>
        {/each}
      {/if}
      {#each points as l (l.id)}
        {@const [x, y] = projection([l.lon, l.lat])}
        <circle cx={x} cy={y} r={(3 + Math.min(6, compte(l))) / Math.sqrt(t.k)} fill="var(--app)" stroke="var(--background)"
                stroke-width="1.5" vector-effect="non-scaling-stroke"
                class="cursor-pointer" role="button" tabindex="0" aria-label={`${l.nom} : ${compte(l)}`}
                onclick={() => onchoisir?.(l.id)} onkeydown={(e) => e.key === 'Enter' && onchoisir?.(l.id)}>
          <title>{l.nom} : {compte(l)}</title>
        </circle>
        {#if t.k >= 4}
          <text x={x} y={y - (8 + Math.min(6, compte(l))) / Math.sqrt(t.k)} font-size={11 / t.k} text-anchor="middle"
                fill="var(--foreground)" stroke="var(--background)" stroke-width={3 / t.k} paint-order="stroke"
                class="pointer-events-none" aria-hidden="true">{l.nom}</text>
        {/if}
      {/each}
    </g>
  </svg>

  <div class="absolute right-2 bottom-2 flex flex-col overflow-hidden rounded-lg border bg-card/90 backdrop-blur" role="group" aria-label="Zoom de la carte">
    <button type="button" class="grid size-8 place-items-center sm:size-10 hover:bg-secondary disabled:opacity-40" aria-label="Zoomer" disabled={t.k >= ZOOM_MAX} onclick={() => zoomer(1.8)}><Plus class="size-4" /></button>
    <button type="button" class="grid size-8 place-items-center sm:size-10 border-t hover:bg-secondary disabled:opacity-40" aria-label="Dézoomer" disabled={t.k <= 1} onclick={() => zoomer(1 / 1.8)}><Minus class="size-4" /></button>
    <button type="button" class="grid size-8 place-items-center sm:size-10 border-t hover:bg-secondary disabled:opacity-40" aria-label="Recentrer la carte" disabled={t.k <= 1} onclick={recentrer}><Maximize class="size-4" /></button>
  </div>
</div>
