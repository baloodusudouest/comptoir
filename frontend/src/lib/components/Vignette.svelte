<script>
  // Photo de la recette (reprise du livre), ou vignette unie à la couleur de l'appli avec l'initiale.
  let { recette, taille = 'md', class: classe = '' } = $props()
  const tailles = { sm: 'size-12 text-lg rounded-lg', md: 'aspect-square w-full text-4xl rounded-xl', lg: 'aspect-square w-full text-6xl rounded-2xl' }
  let rate = $state(false)
</script>

{#if recette.photo && !rate}
  <img src={`/api/photos/${recette.id}`} alt="" loading="lazy" onerror={() => (rate = true)}
       class={`${tailles[taille]} object-cover ${classe}`} />
{:else}
  <div aria-hidden="true" class={`${tailles[taille]} grid place-items-center bg-primary/15 font-light text-primary ${classe}`}>
    {recette.titre.replace(/^(le |la |les |l')/i, '').charAt(0).toUpperCase()}
  </div>
{/if}
