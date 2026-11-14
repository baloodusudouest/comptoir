<script>
  // Au bar : l'écran d'ouverture. Ce qu'on peut faire ce soir, ce qu'il manque de peu, et la bouteille
  // qui en débloquerait le plus. Le geste répété (« un cocktail ce soir ») ne passe derrière aucune tuile.
  import Search from '@lucide/svelte/icons/search'
  import Star from '@lucide/svelte/icons/star'
  import Leaf from '@lucide/svelte/icons/leaf'
  import MapPin from '@lucide/svelte/icons/map-pin'
  import Check from '@lucide/svelte/icons/check'
  import { api } from '$lib/api.js'
  import { etat, recharger, nomsLieux } from '$lib/donnees.svelte.js'
  import Zeste from '$lib/components/Zeste.svelte'
  import CarteCocktail from '$lib/components/CarteCocktail.svelte'

  let recherche = $state('')
  let favoris = $state(false)
  let sansAlcool = $state(false)
  let base = $state('')
  let ajout = $state('')

  const sansAccent = (s) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  function garde(r) {
    if (favoris && !r.favori) return false
    if (sansAlcool && !r.sans_alcool) return false
    if (base && r.base !== base) return false
    if (recherche && !sansAccent(r.titre).includes(sansAccent(recherche))) return false
    return true
  }
  let faisables = $derived(etat.recettes.filter((r) => etat.faisables.has(r.id) && garde(r)))
  let presque = $derived(etat.recettes.filter((r) => etat.presque.has(r.id) && garde(r))
    .sort((a, b) => etat.presque.get(a.id).length - etat.presque.get(b.id).length))

  async function jeLai(ingredient) {
    ajout = ingredient
    try {
      await api.post('/api/bar', { ingredient, present: true })
      await recharger()
    } finally {
      ajout = ''
    }
  }
</script>

<header class="mb-8 flex flex-col gap-6 sm:flex-row sm:items-center sm:gap-10">
  <Zeste valeur={etat.faisables.size} total={etat.recettes.length} libelle={etat.faisables.size > 1 ? 'faisables ce soir' : 'faisable ce soir'} />
  <div class="min-w-0 flex-1">
    <h1 class="titre">Au bar</h1>
    <p class="mt-2 max-w-prose text-muted-foreground">
      {#if !etat.recettes.length}
        Aucun livre pour l'instant. Dépose un livre de cocktails en EPUB dans <a class="text-foreground underline underline-offset-4" href="#/reglages">Réglages</a>.
      {:else}
        {etat.recettes.length} recettes dans tes livres. Ce soir, ton bar en permet {etat.faisables.size}.
      {/if}
    </p>
    <label class="mt-4 flex h-11 max-w-md items-center gap-2 rounded-full border border-input bg-card px-4 focus-within:border-ring">
      <Search class="size-4 text-muted-foreground" aria-hidden="true" />
      <span class="sr-only">Chercher un cocktail</span>
      <input type="search" bind:value={recherche} placeholder="Chercher un cocktail" class="min-w-0 flex-1 bg-transparent outline-none" />
    </label>
  </div>
</header>

<div class="mb-8 flex flex-wrap gap-2" role="group" aria-label="Filtres">
  <button type="button" aria-pressed={favoris} onclick={() => (favoris = !favoris)}
          class="flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-sm aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground">
    <Star class="size-3.5" aria-hidden="true" /> Favoris
  </button>
  <button type="button" aria-pressed={sansAlcool} onclick={() => (sansAlcool = !sansAlcool)}
          class="flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-sm aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground">
    <Leaf class="size-3.5" aria-hidden="true" /> Sans alcool
  </button>
  {#if etat.bases.length}
    <label class="flex h-9 items-center rounded-full border px-3 text-sm has-[option:checked:not([value=''])]:border-primary">
      <span class="sr-only">Spiritueux de base</span>
      <select bind:value={base} class="bg-transparent outline-none">
        <option value="">Tous les spiritueux</option>
        {#each etat.bases as b}<option value={b.id}>{b.nom}</option>{/each}
      </select>
    </label>
  {/if}
  <a href="#/cocktails/lieux" class="flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-sm hover:border-foreground/40">
    <MapPin class="size-3.5" aria-hidden="true" /> Par lieu
  </a>
</div>

{#if etat.debloque.length}
  <section aria-labelledby="titre-debloque" class="mb-10 rounded-2xl border bg-card p-5">
    <h2 id="titre-debloque" class="text-lg font-medium">Une bouteille pour en débloquer le plus</h2>
    <ul class="mt-3 grid gap-2 sm:grid-cols-3">
      {#each etat.debloque as d (d.ingredient)}
        <li class="flex items-center justify-between gap-3 rounded-xl bg-secondary/60 px-4 py-3">
          <span class="min-w-0">
            <span class="block truncate font-medium">{d.nom}</span>
            <span class="text-sm text-primary">+{d.recettes} {d.recettes > 1 ? 'cocktails' : 'cocktail'}</span>
          </span>
          <button type="button" onclick={() => jeLai(d.ingredient)} disabled={ajout === d.ingredient}
                  class="flex h-9 shrink-0 items-center gap-1 rounded-full border px-3 text-sm hover:border-primary hover:text-primary">
            <Check class="size-3.5" aria-hidden="true" /> Je l'ai
          </button>
        </li>
      {/each}
    </ul>
  </section>
{/if}

<section aria-labelledby="titre-faisables" class="mb-12">
  <h2 id="titre-faisables" class="mb-4 text-lg font-medium">Faisables maintenant <span class="font-normal text-muted-foreground">{faisables.length}</span></h2>
  {#if faisables.length}
    <ul aria-label="Faisables maintenant" class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {#each faisables as r (r.id)}
        <li><CarteCocktail recette={r} lieux={nomsLieux(r.evoque)} /></li>
      {/each}
    </ul>
  {:else if etat.recettes.length}
    <p class="max-w-prose text-muted-foreground">
      Rien pour l'instant avec ces filtres. Coche ce que tu as dans <a class="text-foreground underline underline-offset-4" href="#/mon-bar">Mon bar</a>, ou regarde ce qu'il manque de peu juste en dessous.
    </p>
  {/if}
</section>

{#if presque.length}
  <section aria-labelledby="titre-presque">
    <h2 id="titre-presque" class="mb-4 text-lg font-medium">Il te manque 1 ou 2 ingrédients <span class="font-normal text-muted-foreground">{presque.length}</span></h2>
    <ul aria-label="Il manque 1 ou 2 ingrédients" class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {#each presque as r (r.id)}
        <li><CarteCocktail recette={r} manque={etat.presque.get(r.id)} /></li>
      {/each}
    </ul>
  </section>
{/if}
