<script>
  // Conseils : les passages des livres qui ne sont pas des recettes (glace, techniques, verres, matériel…),
  // rangés par thème. Onglet de « Cocktails » : #/cocktails/conseils et #/cocktails/conseils/12 pour en lire un.
  // Le texte vient du livre importé et reste dans la base de la maison.
  import { onMount } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Search from '@lucide/svelte/icons/search'
  import { api } from '$lib/api.js'

  let { id = null } = $props()
  let donnees = $state(null)
  let conseil = $state(null)
  let theme = $state('')
  let recherche = $state('')
  let erreur = $state('')

  const sansAccents = (t) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

  let visibles = $derived.by(() => {
    if (!donnees) return []
    const q = sansAccents(recherche.trim())
    return donnees.conseils.filter((c) => (!theme || c.theme === theme) && (!q || sansAccents(`${c.titre} ${c.apercu}`).includes(q)))
  })
  let parTheme = $derived(donnees ? donnees.themes.map((t) => ({ theme: t, conseils: visibles.filter((c) => c.theme === t) })).filter((g) => g.conseils.length) : [])

  // Les items de liste qui se suivent sont regroupés dans une même liste
  let morceaux = $derived.by(() => {
    if (!conseil) return []
    const res = []
    for (const x of conseil.contenu) {
      const liste = x.sorte === 'li_ul' ? 'ul' : x.sorte === 'li_ol' ? 'ol' : null
      const dernier = res.at(-1)
      if (liste && dernier?.sorte === liste) dernier.items.push(x.texte)
      else if (liste) res.push({ sorte: liste, items: [x.texte] })
      else res.push(x)
    }
    return res
  })

  onMount(async () => {
    try {
      if (id) conseil = await api.get(`/api/conseils/${id}`)
      else donnees = await api.get('/api/conseils')
    } catch (e) {
      erreur = e.message
    }
  })
</script>

{#if erreur}
  <p class="text-destructive" role="alert">{erreur}</p>
{:else if id && conseil}
  <article class="max-w-[68ch]" aria-labelledby="titre-conseil">
    <a href="#/cocktails/conseils" class="mb-5 inline-flex h-10 items-center gap-2 rounded-lg pr-3 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeft class="size-4" aria-hidden="true" /> Tous les conseils
    </a>
    <p class="text-sm font-medium text-primary">{conseil.theme}</p>
    <h2 id="titre-conseil" class="mt-1 text-3xl font-semibold tracking-tight text-balance">{conseil.titre}</h2>
    <p class="mt-2 text-sm text-muted-foreground">{conseil.livre}{conseil.pages ? `, ${conseil.pages}` : ''}</p>
    <div class="mt-6 grid gap-4 text-lg leading-relaxed">
      {#each morceaux as m}
        {#if m.sorte === 'sous_titre'}
          <h3 class="mt-3 text-xl font-semibold">{m.texte}</h3>
        {:else if m.sorte === 'ul'}
          <ul class="grid list-disc gap-1.5 pl-6 marker:text-primary">{#each m.items as t}<li>{t}</li>{/each}</ul>
        {:else if m.sorte === 'ol'}
          <ol class="grid list-decimal gap-1.5 pl-6 marker:text-primary">{#each m.items as t}<li>{t}</li>{/each}</ol>
        {:else}
          <p>{m.texte}</p>
        {/if}
      {/each}
    </div>
  </article>
{:else if donnees}
  {#if !donnees.conseils.length}
    <div class="max-w-xl rounded-2xl border border-dashed p-6">
      <h2 class="text-lg font-semibold">Pas encore de conseils</h2>
      <p class="mt-2 text-muted-foreground">
        {#if donnees.livres}
          Les pages du livre sur la préparation, la glace, les verres et le matériel arriveront ici à l'import du livre complet.
          Un livre importé avant la version 0.2 de Comptoir est à supprimer puis à réimporter pour en tirer ses conseils.
        {:else}
          Dépose un livre dans Réglages : ses pages sur la préparation, la glace, les verres et le matériel arriveront ici.
        {/if}
      </p>
    </div>
  {:else}
    <div class="mb-6 flex flex-wrap items-center gap-2">
      <label class="flex h-10 w-full items-center gap-2 rounded-full border px-3.5 sm:w-64">
        <Search class="size-4 text-muted-foreground" aria-hidden="true" />
        <span class="sr-only">Chercher un conseil</span>
        <input type="search" bind:value={recherche} placeholder="Chercher (glace, shaker…)" class="h-full min-w-0 flex-1 bg-transparent outline-none" />
      </label>
      <div class="flex flex-wrap gap-1.5" role="group" aria-label="Thèmes">
        {#each ['', ...donnees.themes] as t}
          <button type="button" aria-pressed={theme === t} onclick={() => (theme = t)}
                  class="h-10 rounded-full border px-4 text-sm text-muted-foreground hover:text-foreground aria-pressed:border-primary aria-pressed:text-foreground">
            {t || 'Tous'}
          </button>
        {/each}
      </div>
    </div>
    {#if !parTheme.length}
      <p class="text-muted-foreground">Aucun conseil ne parle de « {recherche} ».</p>
    {/if}
    <div class="grid gap-8">
      {#each parTheme as g (g.theme)}
        <section aria-labelledby={`theme-${g.theme}`}>
          <h2 id={`theme-${g.theme}`} class="mb-2 text-lg font-semibold">{g.theme}</h2>
          <ul class="grid gap-x-8 md:grid-cols-2">
            {#each g.conseils as c (c.id)}
              <li class="border-t">
                <a href={`#/cocktails/conseils/${c.id}`} class="block py-3.5 hover:text-primary">
                  <span class="flex items-baseline justify-between gap-3">
                    <span class="font-medium">{c.titre}</span>
                    {#if c.pages}<span class="shrink-0 text-sm text-muted-foreground tabular-nums">{c.pages}</span>{/if}
                  </span>
                  <span class="mt-1 line-clamp-2 block text-sm text-muted-foreground">{c.apercu}</span>
                </a>
              </li>
            {/each}
          </ul>
        </section>
      {/each}
    </div>
  {/if}
{/if}
