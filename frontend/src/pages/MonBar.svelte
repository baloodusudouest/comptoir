<script>
  // Mon bar : les ingrédients que tes livres emploient, par catégorie puis famille. Cocher ce qu'on a.
  // Une famille cochée (« Rhum ») vaut pour les recettes qui demandent « du rhum », pas pour celles qui
  // demandent « du rhum blanc » : cocher la variante exacte quand on la connaît.
  import { onMount } from 'svelte'
  import Search from '@lucide/svelte/icons/search'
  import Check from '@lucide/svelte/icons/check'
  import { api } from '$lib/api.js'
  import { recharger } from '$lib/donnees.svelte.js'

  let donnees = $state(null)
  let recherche = $state('')
  let erreur = $state('')

  const sansAccent = (s) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
  let categories = $derived((donnees?.categories ?? []).map((c) => ({
    ...c,
    familles: c.familles.map((f) => ({ ...f, ingredients: f.ingredients.filter((i) => !recherche || sansAccent(i.nom).includes(sansAccent(recherche)) || sansAccent(f.nom).includes(sansAccent(recherche))) }))
      .filter((f) => f.ingredients.length),
  })).filter((c) => c.familles.length))
  let frais = $derived((donnees?.categories ?? []).flatMap((c) => c.familles.flatMap((f) => f.ingredients)).filter((i) => i.frais))

  async function charger() {
    try { donnees = await api.get('/api/bar') } catch (e) { erreur = e.message }
  }
  async function cocher(i) {
    const avant = i.present
    i.present = !avant                       // tout de suite à l'écran ; remis si le serveur refuse
    try {
      const r = await api.post('/api/bar', { ingredient: i.id, present: !avant })
      donnees.faisables = r.faisables
      recharger()
    } catch (e) {
      i.present = avant
      erreur = e.message
    }
  }
  async function basculerFrais(i) {
    await api.post('/api/frais', { ingredient: i.id, frais: !i.frais })
    i.frais = !i.frais
  }
  onMount(charger)
</script>

<header class="mb-6 flex flex-wrap items-end justify-between gap-4">
  <div>
    <h1 class="titre">Mon bar</h1>
    {#if donnees}<p class="mt-2 text-muted-foreground" role="status">Ce bar permet <span class="text-primary">{donnees.faisables}</span> {donnees.faisables > 1 ? 'cocktails' : 'cocktail'}.</p>{/if}
  </div>
  <label class="flex h-11 w-full max-w-xs items-center gap-2 rounded-full border border-input bg-card px-4 focus-within:border-ring">
    <Search class="size-4 text-muted-foreground" aria-hidden="true" /><span class="sr-only">Filtrer les ingrédients</span>
    <input type="search" bind:value={recherche} placeholder="Filtrer" class="min-w-0 flex-1 bg-transparent outline-none" />
  </label>
</header>

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}

{#snippet caseIngredient(i, famille)}
  <li class="flex items-center justify-between gap-2">
    <button type="button" role="checkbox" aria-checked={i.present || i.toujours_la} disabled={i.toujours_la} onclick={() => cocher(i)}
            class="flex min-h-11 min-w-0 flex-1 items-center gap-3 rounded-lg px-2 text-left hover:bg-secondary/60 disabled:cursor-default disabled:hover:bg-transparent">
      <span class="grid size-5 shrink-0 place-items-center rounded-md border border-input aria-[checked=true]:border-primary" aria-hidden="true"
            class:bg-primary={i.present || i.toujours_la} class:border-primary={i.present || i.toujours_la}>
        {#if i.present || i.toujours_la}<Check class="size-3.5 text-primary-foreground" />{/if}
      </span>
      <span class={`min-w-0 ${i.niveau === 'famille' && famille ? 'font-medium' : ''}`}>
        {i.niveau === 'famille' && famille ? `${i.nom}, sans précision` : i.nom}
        {#if i.toujours_la}<span class="text-sm text-muted-foreground"> (toujours là)</span>{/if}
      </span>
    </button>
    {#if i.frais_propose && !i.toujours_la}
      <button type="button" aria-pressed={i.frais} onclick={() => basculerFrais(i)} title="À racheter souvent"
              class="h-7 shrink-0 rounded-full border px-2.5 text-xs text-muted-foreground aria-pressed:border-primary aria-pressed:text-primary">frais</button>
    {/if}
  </li>
{/snippet}

{#if !donnees}
  <p class="text-muted-foreground">Lecture…</p>
{:else if !donnees.categories.length}
  <p class="max-w-prose text-muted-foreground">Aucun ingrédient pour l'instant : ils apparaissent ici dès qu'un livre est importé (<a class="text-foreground underline underline-offset-4" href="#/reglages">Réglages</a>).</p>
{:else}
  {#if frais.length && !recherche}
    <section aria-labelledby="titre-frais" class="mb-8 rounded-2xl border bg-card p-5">
      <h2 id="titre-frais" class="text-lg font-medium">À racheter souvent</h2>
      <ul class="mt-2 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
        {#each frais as i (i.id)}{@render caseIngredient(i, false)}{/each}
      </ul>
    </section>
  {/if}
  <div class="columns-1 gap-6 md:columns-2 xl:columns-3">
    {#each categories as c (c.id)}
      <section aria-labelledby={`cat-${c.id}`} class="mb-6 break-inside-avoid rounded-2xl border bg-card p-5">
        <h2 id={`cat-${c.id}`} class="text-lg font-medium">{c.nom}</h2>
        {#each c.familles as f (f.id)}
          {#if f.ingredients.length > 1}
            <h3 class="mt-4 mb-1 text-sm text-muted-foreground">{f.nom}</h3>
          {/if}
          <!-- Une famille sans variante (Liqueur de banane) : une seule case, sans le nom répété au-dessus -->
          <ul aria-label={f.nom} class={f.ingredients.length > 1 ? '' : 'mt-1'}>
            {#each f.ingredients as i (i.id)}{@render caseIngredient(i, f.ingredients.length > 1)}{/each}
          </ul>
        {/each}
      </section>
    {/each}
  </div>
{/if}
