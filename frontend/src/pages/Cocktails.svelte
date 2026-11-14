<script>
  // Cocktails : toutes les recettes (filtres), « Par lieu » (liste pays › région › ville, et carte embarquée)
  // ou « Conseils » (les pages des livres qui ne sont pas des recettes).
  import Conseils from './Conseils.svelte'
  import Star from '@lucide/svelte/icons/star'
  import MapIcon from '@lucide/svelte/icons/map'
  import List from '@lucide/svelte/icons/list'
  import { etat, nomsLieux, vues } from '$lib/donnees.svelte.js'
  import CarteCocktail from '$lib/components/CarteCocktail.svelte'
  import CarteMonde from '$lib/components/CarteMonde.svelte'

  let { sous = '', detail = null } = $props()

  // ---------------------------------------------------------------- liste
  // Valeurs reprises de « vues » : le retour depuis une fiche retrouve les mêmes filtres
  let livre = $state(vues.liste.livre)
  let base = $state(vues.liste.base)
  let quoi = $state(vues.liste.quoi)        // tout, faisables, presque
  let favoris = $state(vues.liste.favoris)
  $effect(() => { Object.assign(vues.liste, { livre, base, quoi, favoris }) })
  let livres = $derived([...new Map(etat.recettes.map((r) => [r.livre_id, r.livre])).entries()].sort((a, b) => a[1].localeCompare(b[1], 'fr', { sensitivity: 'base' })))
  const numero = (p) => parseInt((p || '').replace(/^p\. /, ''), 10) || 0
  let liste = $derived(etat.recettes.filter((r) =>
      (!livre || String(r.livre_id) === livre) && (!base || r.base === base) && (!favoris || r.favori) &&
      (quoi === 'tout' || (quoi === 'faisables' ? etat.faisables.has(r.id) : etat.presque.has(r.id))))
    .sort((a, b) => (livre ? numero(a.pages) - numero(b.pages) : 0) || etat.recettes.indexOf(a) - etat.recettes.indexOf(b)))   // ordre alphabétique donné par le serveur

  // ---------------------------------------------------------------- par lieu
  let sorte = $state(vues.lieux.sorte)   // cree_a, evoque, les-deux
  let carte = $state(vues.lieux.carte)
  let choisi = $state(vues.lieux.choisi)
  $effect(() => { Object.assign(vues.lieux, { sorte, carte, choisi }) })
  const ids = (l) => sorte === 'cree_a' ? l.cree_a : sorte === 'evoque' ? l.evoque : [...new Set([...l.cree_a, ...l.evoque])]
  let lieux = $derived([...etat.lieux.values()])
  let arbre = $derived.by(() => {
    const avec = lieux.filter((l) => ids(l).length)
    // De A à Z à chaque niveau (pays, régions, villes), accents compris ; le nombre de cocktails est affiché à côté
    const alpha = (a, b) => a.nom.localeCompare(b.nom, 'fr', { sensitivity: 'base' })
    const enfants = (parent) => avec.filter((l) => l.parent === parent).sort(alpha)
    return avec.filter((l) => l.type === 'pays').sort(alpha)
      .map((p) => ({ ...p, sous: enfants(p.id).map((r) => ({ ...r, sous: enfants(r.id).map((v) => ({ ...v, sous: enfants(v.id) })) })) }))
  })
  let recettesChoisies = $derived(choisi ? etat.recettes.filter((r) => ids(etat.lieux.get(choisi)).includes(r.id)) : [])
  function choisir(id) {
    choisi = choisi === id ? null : id
  }
</script>

<header class="mb-6 flex flex-wrap items-end justify-between gap-4">
  <h1 class="titre">Cocktails</h1>
  <nav aria-label="Vue" class="flex rounded-full border p-1 text-sm">
    <a href="#/cocktails" aria-current={sous !== 'lieux' && sous !== 'conseils' ? 'page' : undefined} class="rounded-full px-4 py-1.5 text-muted-foreground aria-[current=page]:bg-secondary aria-[current=page]:text-foreground">Tous</a>
    <a href="#/cocktails/lieux" aria-current={sous === 'lieux' ? 'page' : undefined} class="rounded-full px-4 py-1.5 text-muted-foreground aria-[current=page]:bg-secondary aria-[current=page]:text-foreground">Par lieu</a>
    <a href="#/cocktails/conseils" aria-current={sous === 'conseils' ? 'page' : undefined} class="rounded-full px-4 py-1.5 text-muted-foreground aria-[current=page]:bg-secondary aria-[current=page]:text-foreground">Conseils</a>
  </nav>
</header>

{#if sous === 'conseils'}
  <Conseils id={detail} />
{:else if sous !== 'lieux'}
  <div class="mb-6 flex flex-wrap gap-2" role="group" aria-label="Filtres">
    <label class="flex h-9 items-center rounded-full border px-3 text-sm"><span class="sr-only">Livre</span>
      <select bind:value={livre} class="max-w-56 bg-transparent outline-none">
        <option value="">Tous les livres</option>
        {#each livres as [id, titre]}<option value={String(id)}>{titre}</option>{/each}
      </select>
    </label>
    <label class="flex h-9 items-center rounded-full border px-3 text-sm"><span class="sr-only">Spiritueux</span>
      <select bind:value={base} class="bg-transparent outline-none">
        <option value="">Tous les spiritueux</option>
        {#each etat.bases as b}<option value={b.id}>{b.nom}</option>{/each}
      </select>
    </label>
    <label class="flex h-9 items-center rounded-full border px-3 text-sm"><span class="sr-only">Ce que le bar permet</span>
      <select bind:value={quoi} class="bg-transparent outline-none">
        <option value="tout">Toutes</option>
        <option value="faisables">Faisables</option>
        <option value="presque">Il manque 1 ou 2</option>
      </select>
    </label>
    <button type="button" aria-pressed={favoris} onclick={() => (favoris = !favoris)}
            class="flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-sm aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground">
      <Star class="size-3.5" aria-hidden="true" /> Favoris
    </button>
  </div>
  <p class="mb-4 text-sm text-muted-foreground">{liste.length} {liste.length > 1 ? 'recettes' : 'recette'}{livre ? ', dans l\'ordre des pages du livre' : ''}</p>
  <ul aria-label="Recettes" class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
    {#each liste as r (r.id)}
      <li><CarteCocktail recette={r} manque={etat.presque.get(r.id)} lieux={nomsLieux([...r.cree_a, ...r.evoque])} /></li>
    {/each}
  </ul>
{:else}
  <div class="mb-5 flex flex-wrap items-center gap-2">
    <div class="flex rounded-full border p-1 text-sm" role="radiogroup" aria-label="Sorte de lieu">
      {#each [['les-deux', 'Les deux'], ['cree_a', 'Créé à'], ['evoque', 'Évoque']] as [v, nom]}
        <button type="button" role="radio" aria-checked={sorte === v} onclick={() => (sorte = v)}
                class="rounded-full px-3.5 py-1.5 text-muted-foreground aria-checked:bg-secondary aria-checked:text-foreground">{nom}</button>
      {/each}
    </div>
    <button type="button" onclick={() => (carte = !carte)} class="flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-sm">
      {#if carte}<List class="size-3.5" aria-hidden="true" /> Liste{:else}<MapIcon class="size-3.5" aria-hidden="true" /> Carte{/if}
    </button>
  </div>
  <p class="mb-5 max-w-prose text-sm text-muted-foreground">
    « Créé à » : là où le cocktail a été inventé, d'après le livre ou Wikidata. « Évoque » : le lieu que suggère son nom (Mexican Mule, le Mexique).
  </p>

  {#if !arbre.length}
    <p class="text-muted-foreground">Aucun lieu pour l'instant. Les lieux évoqués par les noms et les origines écrites dans les livres apparaissent ici après l'import.</p>
  {:else}
    <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div class="min-w-0">
        {#if carte}
          <div class="rounded-2xl border bg-card p-2"><CarteMonde {lieux} {sorte} {choisi} onchoisir={choisir} /></div>
        {:else}
          <ul aria-label="Lieux" class="divide-y rounded-2xl border bg-card">
            {#snippet ligne(l, retrait)}
              <button type="button" onclick={() => choisir(l.id)} aria-pressed={choisi === l.id}
                      class="flex w-full items-center justify-between gap-3 py-2.5 pr-4 text-left hover:bg-secondary/50 aria-pressed:text-primary"
                      style={`padding-left: ${1 + retrait * 1.25}rem`}>
                <span class={retrait ? 'text-sm' : 'font-medium'}>{l.nom}</span>
                <span class="text-sm tabular-nums text-muted-foreground">{ids(l).length}</span>
              </button>
            {/snippet}
            {#each arbre as p (p.id)}
              <li>
                {@render ligne(p, 0)}
                {#each p.sous as r (r.id)}
                  {@render ligne(r, 1)}
                  {#each r.sous as v (v.id)}
                    {@render ligne(v, 2)}
                    {#each v.sous as q (q.id)}{@render ligne(q, 3)}{/each}
                  {/each}
                {/each}
              </li>
            {/each}
          </ul>
        {/if}
      </div>
      <section aria-live="polite" class="min-w-0">
        {#if choisi}
          <h2 class="mb-4 text-lg font-medium">{etat.lieux.get(choisi).chemin.join(' › ')}</h2>
          <ul aria-label="Recettes du lieu" class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3">
            {#each recettesChoisies as r (r.id)}
              <li><CarteCocktail recette={r} manque={etat.presque.get(r.id)} /></li>
            {/each}
          </ul>
        {:else}
          <p class="text-muted-foreground">Choisis un lieu pour voir ses cocktails.</p>
        {/if}
      </section>
    </div>
  {/if}
{/if}
