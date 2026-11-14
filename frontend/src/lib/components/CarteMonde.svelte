<script>
  // Carte du monde embarquée (world-atlas, 110 m) : rien n'est demandé à Internet.
  // Les pays qui ont des cocktails prennent la couleur de l'appli ; villes et régions sont des points.
  import { geoNaturalEarth1, geoPath } from 'd3-geo'
  import { feature } from 'topojson-client'
  import monde from 'world-atlas/countries-110m.json'

  let { lieux = [], sorte = 'les-deux', choisi = null, onchoisir } = $props()

  const L = 960, H = 500
  const pays = feature(monde, monde.objects.countries).features
  const projection = geoNaturalEarth1().fitSize([L, H], { type: 'Sphere' })
  const chemin = geoPath(projection)

  const compte = (l) => sorte === 'cree_a' ? l.cree_a.length : sorte === 'evoque' ? l.evoque.length : new Set([...l.cree_a, ...l.evoque]).size
  let parIso = $derived(new Map(lieux.filter((l) => l.type === 'pays' && l.iso && compte(l)).map((l) => [String(l.iso).padStart(3, '0'), l])))
  let points = $derived(lieux.filter((l) => l.type !== 'pays' && compte(l)))
  let maxi = $derived(Math.max(1, ...[...parIso.values()].map(compte)))
</script>

<svg viewBox={`0 0 ${L} ${H}`} class="w-full" role="img" aria-label="Carte du monde des cocktails">
  <path d={chemin({ type: 'Sphere' })} fill="var(--card)" />
  {#each pays as p, i (i)}
    {@const l = parIso.get(String(p.id))}
    <path d={chemin(p)} stroke="var(--background)" stroke-width="0.5"
          fill={l ? 'var(--app)' : 'var(--secondary)'}
          fill-opacity={l ? 0.35 + 0.65 * (compte(l) / maxi) : 1}
          class={l ? 'cursor-pointer' : ''}
          stroke-opacity={l && choisi === l.id ? 1 : 0.8}
          role={l ? 'button' : undefined} tabindex={l ? 0 : undefined} aria-label={l ? `${l.nom} : ${compte(l)}` : undefined}
          onclick={() => l && onchoisir?.(l.id)} onkeydown={(e) => l && e.key === 'Enter' && onchoisir?.(l.id)}>
      {#if l}<title>{l.nom} : {compte(l)}</title>{/if}
    </path>
  {/each}
  {#each points as l (l.id)}
    {@const [x, y] = projection([l.lon, l.lat])}
    <circle cx={x} cy={y} r={3 + Math.min(6, compte(l))} fill="var(--app)" stroke="var(--background)" stroke-width="1.5"
            class="cursor-pointer" role="button" tabindex="0" aria-label={`${l.nom} : ${compte(l)}`}
            onclick={() => onchoisir?.(l.id)} onkeydown={(e) => e.key === 'Enter' && onchoisir?.(l.id)}>
      <title>{l.nom} : {compte(l)}</title>
    </circle>
  {/each}
</svg>
