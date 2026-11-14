<script>
  // Un cocktail dans une liste : vignette, nom façon carte de bar, livre et page du livre papier,
  // et, s'il manque quelque chose, ce qui manque (en orange).
  // Pastilles sur la vignette, lisibles sur les photos à fond blanc : coche verte = faisable avec le bar ; étoile = favori.
  import Star from '@lucide/svelte/icons/star'
  import Check from '@lucide/svelte/icons/check'
  import Vignette from './Vignette.svelte'
  import { etat, source } from '$lib/donnees.svelte.js'

  let { recette, manque = null, lieux = null } = $props()
  let faisable = $derived(etat.faisables.has(recette.id))
</script>

<a href={`#/cocktail/${recette.id}`} class="group flex min-w-0 flex-col gap-2.5 rounded-2xl p-1.5 -m-1.5 transition-colors hover:bg-secondary/60">
  <div class="relative">
    <Vignette {recette} />
    {#if faisable || recette.favori}
      <span class="absolute top-2 right-2 flex gap-1.5">
        {#if faisable}
          <span class="grid size-7 place-items-center rounded-full bg-valide text-background shadow-md ring-2 ring-background/70"
                title="Tu as de quoi le faire"><Check class="size-4" strokeWidth={3} aria-hidden="true" /><span class="sr-only">Faisable avec ton bar</span></span>
        {/if}
        {#if recette.favori}
          <span class="grid size-7 place-items-center rounded-full bg-background/85 shadow-md ring-2 ring-background/70"
                title="Favori"><Star class="size-4 fill-primary text-primary" aria-hidden="true" /><span class="sr-only">Favori</span></span>
        {/if}
      </span>
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
