<script>
  // Un cocktail dans une liste : vignette, nom façon carte de bar, livre et page du livre papier,
  // et, s'il manque quelque chose, ce qui manque (en orange).
  import Star from '@lucide/svelte/icons/star'
  import Vignette from './Vignette.svelte'
  import { source } from '$lib/donnees.svelte.js'

  let { recette, manque = null, lieux = null } = $props()
</script>

<a href={`#/cocktail/${recette.id}`} class="group flex min-w-0 flex-col gap-2.5 rounded-2xl p-1.5 -m-1.5 transition-colors hover:bg-secondary/60">
  <div class="relative">
    <Vignette {recette} />
    {#if recette.favori}
      <Star class="absolute top-2 right-2 size-4 fill-primary text-primary drop-shadow" aria-label="Favori" />
    {/if}
  </div>
  <div class="min-w-0 px-0.5">
    <p class="carte-nom-petit text-foreground">{recette.titre}</p>
    <p class="mt-0.5 truncate text-xs text-muted-foreground">{source(recette)}</p>
    {#if manque?.length}
      <p class="mt-1 text-xs text-primary">Il manque {manque.map((m) => m.nom).join(' et ')}</p>
    {:else if lieux}
      <p class="mt-1 truncate text-xs text-muted-foreground">{lieux}</p>
    {/if}
  </div>
</a>
