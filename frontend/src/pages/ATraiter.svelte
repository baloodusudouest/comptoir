<script>
  // À traiter : une tuile par type de question, avec son nombre. Une tuile ouvre sa liste.
  // Rien n'est décidé seul : recettes douteuses, noms d'ingrédients inconnus, origines incertaines, lieux ambigus.
  import { onMount } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import { api } from '$lib/api.js'
  import { recharger } from '$lib/donnees.svelte.js'
  import { Button } from '$lib/components/ui/button/index.js'

  let { sous = '' } = $props()
  let donnees = $state(null)
  let ingredients = $state([])
  let erreur = $state('')
  let choix = $state({})       // id de la question → valeur saisie

  const explications = {
    recette: 'Le découpage de ces recettes est incertain : compare avec le livre, puis valide ou corrige.',
    ingredient: 'Noms d\'ingrédients que Comptoir ne reconnaît pas. Une réponse vaut pour toutes les recettes qui les emploient.',
    origine: 'Wikidata propose plusieurs origines, ou une origine que Comptoir ne situe pas.',
    evoque: 'Ces noms ressemblent à un lieu, mais peuvent vouloir dire autre chose.',
  }

  async function charger() {
    try {
      donnees = await api.get('/api/a-traiter')
      if (sous === 'ingredient' && !ingredients.length) ingredients = await api.get('/api/ingredients')
    } catch (e) { erreur = e.message }
  }
  async function repondre(q, corps) {
    erreur = ''
    try {
      await api.post(`/api/a-traiter/${q.id}`, corps)
      await Promise.all([charger(), recharger()])
    } catch (e) { erreur = e.message }
  }
  async function ignorerRecette(q) {
    await api.post(`/api/recettes/${q.recette_id}/ignorer`)
    await Promise.all([charger(), recharger()])
  }
  let elements = $derived((donnees?.elements ?? []).filter((e) => e.type === sous))
  let parents = $derived(ingredients.filter((i) => i.niveau !== 'variante'))
  const parNom = (nom) => ingredients.find((i) => i.chemin.join(' › ') === nom || i.nom === nom)
  onMount(charger)
</script>

{#if !sous}
  <h1 class="titre mb-6">À traiter</h1>
  {#if erreur}<p class="text-destructive" role="alert">{erreur}</p>{/if}
  {#if donnees}
    {@const pleines = donnees.tuiles.filter((t) => t.nombre)}
    {#if !pleines.length}
      <p class="text-muted-foreground">Rien à traiter. Les questions arrivent ici quand un livre importé laisse un doute.</p>
    {:else}
      <ul aria-label="Questions" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {#each pleines as t (t.type)}
          <li>
            <a href={`#/a-traiter/${t.type}`} class="flex h-full flex-col justify-between gap-6 rounded-2xl border bg-card p-5 hover:border-primary/60">
              <span class="chiffre text-5xl text-primary">{t.nombre}</span>
              <span class="font-medium">{t.nom}</span>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
{:else}
  <a href="#/a-traiter" class="mb-5 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft class="size-4" aria-hidden="true" /> À traiter</a>
  <h1 class="titre">{donnees?.tuiles.find((t) => t.type === sous)?.nom ?? 'À traiter'}</h1>
  <p class="mt-2 mb-6 max-w-prose text-muted-foreground">{explications[sous]}</p>
  {#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}
  {#if donnees && !elements.length}
    <p class="text-muted-foreground">Tout est réglé ici.</p>
  {/if}
  <ul aria-label="Liste à traiter" class="grid gap-4">
    {#each elements as q (q.id)}
      <li class="rounded-2xl border bg-card p-5">
        {#if q.type === 'recette'}
          <p class="carte-nom-petit">{q.recette_titre}</p>
          <p class="mt-1 text-sm text-muted-foreground">{q.livre} : {q.donnees.raisons?.join(', ')}</p>
          <pre class="mt-3 max-h-40 overflow-auto rounded-lg bg-secondary/50 p-3 font-sans text-sm whitespace-pre-wrap">{q.texte_original}</pre>
          <div class="mt-4 flex flex-wrap gap-2">
            <Button href={`#/cocktail/${q.recette_id}`}>Ouvrir et corriger</Button>
            <Button variant="outline" onclick={() => repondre(q, { action: 'valider' })}>Valider tel quel</Button>
            <Button variant="ghost" onclick={() => ignorerRecette(q)}>Ce n'est pas une recette</Button>
          </div>
        {:else if q.type === 'ingredient'}
          <p><span class="font-medium">« {q.donnees.nom} »</span>{' '}<span class="text-sm text-muted-foreground">dans {q.recettes} {q.recettes > 1 ? 'recettes' : 'recette'}, par exemple « {q.donnees.texte} » ({q.recette_titre})</span></p>
          <div class="mt-4 flex flex-wrap items-end gap-2">
            {#if q.donnees.proposition}
              <Button onclick={() => repondre(q, { ingredient: q.donnees.proposition })}>C'est : {q.donnees.proposition_nom}</Button>
            {/if}
            <label class="flex flex-col gap-1 text-sm">Rattacher à
              <input list="tous-ingredients" bind:value={choix[q.id]} placeholder="Chercher un ingrédient"
                     class="h-10 w-64 rounded-lg border border-input bg-transparent px-3 outline-none focus:border-ring" />
            </label>
            <Button variant="outline" disabled={!parNom(choix[q.id] ?? '')} onclick={() => repondre(q, { ingredient: parNom(choix[q.id]).id })}>Rattacher</Button>
            <label class="flex flex-col gap-1 text-sm">ou créer dans
              <select bind:value={choix[`p${q.id}`]} class="h-10 w-56 rounded-lg border border-input bg-card px-2">
                <option value="">Choisir…</option>
                {#each parents as p}<option value={p.id}>{p.chemin.join(' › ')}</option>{/each}
              </select>
            </label>
            <Button variant="outline" disabled={!choix[`p${q.id}`]} onclick={() => repondre(q, { action: 'creer', parent: choix[`p${q.id}`], nom: q.donnees.nom })}>Créer</Button>
            <Button variant="ghost" onclick={() => repondre(q, { action: 'ignorer' })}>Laisser inconnu</Button>
          </div>
        {:else if q.type === 'origine'}
          <p><span class="carte-nom-petit">{q.recette_titre}</span>{' '}<span class="text-sm text-muted-foreground">({q.livre})</span></p>
          <p class="mt-2 text-sm text-muted-foreground">Origines trouvées dans Wikidata :</p>
          <div class="mt-3 flex flex-wrap gap-2">
            {#each q.donnees.candidats as c}
              {#if c.lieu}
                <Button variant="outline" onclick={() => repondre(q, { lieu: c.lieu, preuve: `https://www.wikidata.org/wiki/${c.element}` })}>{c.chemin.join(' › ')}</Button>
              {:else}
                <span class="rounded-lg border border-dashed px-3 py-2 text-sm text-muted-foreground">{c.libelle} (lieu inconnu de Comptoir)</span>
              {/if}
            {/each}
            <Button variant="ghost" onclick={() => repondre(q, {})}>Aucune</Button>
          </div>
        {:else if q.type === 'evoque'}
          <p><span class="carte-nom-petit">{q.recette_titre}</span> évoque-t-il <span class="font-medium">{q.donnees.chemin.slice().reverse().join(', ')}</span> ?</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <Button onclick={() => repondre(q, { action: 'oui' })}>Oui</Button>
            <Button variant="outline" onclick={() => repondre(q, { action: 'non' })}>Non</Button>
          </div>
        {/if}
      </li>
    {/each}
  </ul>
  <datalist id="tous-ingredients">
    {#each ingredients as i}<option value={i.chemin.join(' › ')}></option>{/each}
  </datalist>
{/if}
