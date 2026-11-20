<script>
  // Navigation commune aux applis : rail à gauche sur PC, pilule d'icônes en bas sur iPhone.
  // Six entrées : Au bar (ouverture, le geste répété), Cocktails, Mon bar, À traiter, Connexion, Réglages.
  // Adresses : #/ · #/cocktails · #/cocktails/lieux · #/cocktails/conseils · #/cocktails/conseils/5 · #/cocktail/12 ·
  // #/cocktail/12/preparer · #/mon-bar · #/a-traiter · #/connexion · #/reglages
  import { onMount, tick } from 'svelte'
  import { fade } from 'svelte/transition'
  import Martini from '@lucide/svelte/icons/martini'
  import BookOpen from '@lucide/svelte/icons/book-open'
  import Wine from '@lucide/svelte/icons/wine'
  import Inbox from '@lucide/svelte/icons/inbox'
  import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal'
  import Plug from '@lucide/svelte/icons/plug'
  import { api } from '$lib/api.js'
  import { etat, recharger } from '$lib/donnees.svelte.js'
  import Connexion from './pages/Connexion.svelte'
  import AuBar from './pages/AuBar.svelte'
  import Cocktails from './pages/Cocktails.svelte'
  import Fiche from './pages/Fiche.svelte'
  import Preparer from './pages/Preparer.svelte'
  import MonBar from './pages/MonBar.svelte'
  import ATraiter from './pages/ATraiter.svelte'
  import Reglages from './pages/Reglages.svelte'
  import Services from '$lib/services/Services.svelte'   // 0.8.0 : écran commun (contrat 3, socle 0.11.0)

  const onglets = [
    { page: 'au-bar', nom: 'Au bar', icone: Martini, lien: '#/' },
    { page: 'cocktails', nom: 'Cocktails', icone: BookOpen, lien: '#/cocktails' },
    { page: 'mon-bar', nom: 'Mon bar', icone: Wine, lien: '#/mon-bar' },
    { page: 'a-traiter', nom: 'À traiter', icone: Inbox, lien: '#/a-traiter' },
    { page: 'connexion', nom: 'Connexion', icone: Plug, lien: '#/connexion' },
    { page: 'reglages', nom: 'Réglages', icone: SlidersHorizontal, lien: '#/reglages' },
  ]

  let connecte = $state(null) // null : on ne sait pas encore
  let session = $state({ version: '', mistral: false, recherche_web: true })
  let route = $state(lireRoute())

  function lireRoute() {
    const morceaux = location.hash.replace(/^#\/?/, '').split('?')[0].split('/').filter(Boolean)
    if (morceaux[0] === 'cocktail' && /^\d+$/.test(morceaux[1] || '')) {
      return { page: 'cocktails', fiche: Number(morceaux[1]), preparer: morceaux[2] === 'preparer' }
    }
    const page = onglets.some((o) => o.page === morceaux[0]) ? morceaux[0] : 'au-bar'
    return { page, sous: morceaux[1] || '', detail: /^\d+$/.test(morceaux[2] || '') ? Number(morceaux[2]) : null }
  }

  // Position dans la page, gardée par adresse : en revenant d'une fiche, la liste (ou les lieux) reprend où on était
  const positions = new Map()
  let adresse = location.hash
  async function changerDePage() {
    positions.set(adresse, window.scrollY)
    adresse = location.hash
    route = lireRoute()
    await tick()
    requestAnimationFrame(() => window.scrollTo(0, route.fiche ? 0 : positions.get(adresse) ?? 0))
  }

  async function verifier() {
    try {
      session = await api.get('/api/session')
      connecte = session.connecte
      if (connecte) await recharger()
    } catch {
      connecte = false
    }
  }

  async function deconnecter() {
    try { await api.post('/api/deconnexion') } catch { /* déjà déconnecté */ }
    connecte = false
  }

  onMount(verifier)
</script>

<svelte:window onhashchange={changerDePage} oncomptoir-deconnecte={() => (connecte = false)} />

{#if connecte === false}
  <Connexion onconnecte={verifier} />
{:else if connecte && route.preparer}
  <!-- Mode Préparer : plein écran, sans navigation (rien entre le pouce et le bouton) -->
  <Preparer id={route.fiche} />
{:else if connecte}
  <div class="md:pl-52">
    <nav
      aria-label="Sections"
      class="fixed bottom-[calc(0.75rem+env(safe-area-inset-bottom))] left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-full border bg-card/85 p-1.5 shadow-lg backdrop-blur-md
             md:inset-y-0 md:left-0 md:w-52 md:translate-x-0 md:flex-col md:items-stretch md:gap-1 md:rounded-none md:border-0 md:border-r md:bg-transparent md:p-4 md:shadow-none md:backdrop-blur-none"
    >
      <span class="mb-5 hidden px-2 text-xl font-light tracking-[0.12em] uppercase md:block">Comptoir</span>
      {#each onglets as o}
        {@const Icone = o.icone}
        <a
          href={o.lien}
          aria-label={o.nom}
          aria-current={route.page === o.page ? 'page' : undefined}
          class="relative flex h-11 items-center gap-2 rounded-full px-3.5 text-sm font-medium text-muted-foreground transition-colors
                 hover:text-foreground aria-[current=page]:bg-foreground aria-[current=page]:text-background
                 md:h-10 md:rounded-lg md:px-3 md:aria-[current=page]:bg-secondary md:aria-[current=page]:text-foreground"
        >
          <Icone class="size-[1.15rem]" aria-hidden="true" />
          <span class="sr-only md:not-sr-only">{o.nom}</span>
          {#if o.page === 'a-traiter' && etat.aTraiter}
            <span class="absolute top-1 right-1 grid h-4 min-w-4 place-items-center rounded-full bg-primary px-1 text-[0.65rem] font-semibold text-primary-foreground
                         md:static md:ml-auto md:h-5 md:min-w-5 md:text-xs" aria-label={`${etat.aTraiter} à traiter`}>{etat.aTraiter}</span>
          {/if}
        </a>
      {/each}
    </nav>

    <main
      class="mx-auto max-w-6xl px-[max(1rem,env(safe-area-inset-left))] pt-[calc(1.25rem+env(safe-area-inset-top))] pb-[calc(6.5rem+env(safe-area-inset-bottom))] md:px-8 md:pt-8 md:pb-12"
    >
      {#key route.page + (route.fiche ?? '') + (route.sous ?? '') + (route.detail ?? '')}
        <div in:fade={{ duration: 140 }}>
          {#if route.fiche}
            <Fiche id={route.fiche} {session} />
          {:else if route.page === 'cocktails'}
            <Cocktails sous={route.sous} detail={route.detail} />
          {:else if route.page === 'mon-bar'}
            <MonBar />
          {:else if route.page === 'a-traiter'}
            <ATraiter {session} sous={route.sous} />
          {:else if route.page === 'connexion'}
            <Services ondeconnecte={() => (connecte = false)} />
          {:else if route.page === 'reglages'}
            <Reglages {session} {deconnecter} />
          {:else}
            <AuBar />
          {/if}
        </div>
      {/key}
    </main>
  </div>
{/if}
