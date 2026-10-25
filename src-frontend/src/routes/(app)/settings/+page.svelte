<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { api } from '$lib/api/commands';
  import { ApiError } from '$lib/api/client';
  import Icon from '$lib/components/Icon.svelte';
  import { authToken, currentUser, logout } from '$lib/stores/auth';
  import { resetDashboard } from '$lib/stores/dashboard';
  import { loadSystemStatus, systemLoading, systemStatus } from '$lib/stores/system';
  import { resetTransactions } from '$lib/stores/transactions';
  import { bumpData, pushToast, setTheme, theme } from '$lib/stores/ui';
  import { loadWallets, resetWallets, wallets } from '$lib/stores/wallets';
  import { formatDate, initials } from '$lib/utils/format';

  let uri = $state('');
  let dbName = $state('finance_app');
  let dbNameEdited = $state(false);
  let showUri = $state(false);
  let savingDb = $state(false);
  let dbError = $state<string | null>(null);
  let seeding = $state(false);

  const connected = $derived($systemStatus?.db_connected ?? false);
  const sourceLabel = $derived(
    (() => {
      switch ($systemStatus?.config_source) {
        case 'file':
          return 'Disimpan di perangkat ini';
        case 'env':
          return 'Build / environment';
        case 'mock':
          return 'Mock browser (localStorage)';
        default:
          return 'Belum diatur';
      }
    })()
  );

  onMount(() => {
    void (async () => {
      await loadSystemStatus();
      const current = get(systemStatus)?.db_name;
      if (!dbNameEdited && current && current !== '—') {
        dbName = current;
      }
    })();
    void loadWallets();
  });

  async function saveConnection(event: SubmitEvent) {
    event.preventDefault();
    if (savingDb) return;
    const value = uri.trim();
    if (!value.startsWith('mongodb://') && !value.startsWith('mongodb+srv://')) {
      dbError = 'Connection string harus diawali mongodb:// atau mongodb+srv://.';
      return;
    }
    if (value.length < 12 || value.length > 2048) {
      dbError = 'Panjang connection string tidak valid.';
      return;
    }

    savingDb = true;
    dbError = null;
    try {
      await api.setMongoConnection(value, dbName.trim() || 'finance_app');
      pushToast('Koneksi database berhasil disimpan. Memuat ulang aplikasi…');
      resetWallets();
      resetDashboard();
      resetTransactions();
      setTimeout(() => window.location.reload(), 900);
    } catch (caught) {
      dbError = caught instanceof ApiError ? caught.message : 'Gagal menyimpan koneksi database.';
    } finally {
      savingDb = false;
    }
  }

  async function seedDemo() {
    const token = get(authToken);
    if (!token || seeding) return;
    seeding = true;
    try {
      const response = await api.seedDemo(token);
      pushToast(response.message, response.message.includes('dibuat') ? 'success' : 'info');
      bumpData();
      await loadWallets(true);
    } catch (caught) {
      pushToast(caught instanceof Error ? caught.message : 'Gagal membuat data contoh.', 'error');
    } finally {
      seeding = false;
    }
  }

  async function handleLogout() {
    await logout();
  }
</script>

<div class="space-y-5">
  <header>
    <h2 class="text-2xl font-semibold tracking-tight">Pengaturan</h2>
    <p class="mt-1 text-sm text-base-content/45">
      Kelola akun, tampilan, dan koneksi database Anda.
    </p>
  </header>

  <div class="grid gap-4 lg:grid-cols-2">
    <section class="surface p-5">
      <div class="flex items-center gap-2">
        <span class="grid size-8 place-items-center rounded-xl bg-primary/12 text-primary">
          <Icon name="user" size={16} />
        </span>
        <div>
          <h3 class="text-sm font-semibold">Akun</h3>
          <p class="text-[11px] text-base-content/45">Profil yang sedang aktif</p>
        </div>
      </div>

      <div class="mt-5 flex items-center gap-4">
        <div
          class="grid size-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/20 text-lg font-bold text-primary"
        >
          {initials($currentUser?.name ?? 'Pengguna')}
        </div>
        <div class="min-w-0">
          <p class="truncate text-base font-semibold">{$currentUser?.name ?? '—'}</p>
          <p class="truncate text-xs text-base-content/50">{$currentUser?.email ?? '—'}</p>
          <span class="badge badge-ghost badge-sm mt-1.5"
            >{$currentUser?.base_currency ?? 'IDR'}</span
          >
        </div>
      </div>

      <dl class="mt-5 space-y-2 border-t border-base-content/8 pt-4 text-xs">
        <div class="flex justify-between gap-4">
          <dt class="text-base-content/45">Bergabung sejak</dt>
          <dd class="font-medium">
            {$currentUser ? formatDate($currentUser.created_at) : '—'}
          </dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-base-content/45">ID pengguna</dt>
          <dd class="max-w-[12rem] truncate font-mono text-[10px] text-base-content/55">
            {$currentUser?.id ?? '—'}
          </dd>
        </div>
      </dl>

      <button
        type="button"
        class="btn btn-ghost btn-sm mt-4 w-full justify-start text-error"
        onclick={handleLogout}
      >
        <Icon name="logout" size={16} />
        Keluar dari akun
      </button>
    </section>

    <section class="surface p-5">
      <div class="flex items-center gap-2">
        <span class="grid size-8 place-items-center rounded-xl bg-secondary/12 text-secondary">
          <Icon name="sun" size={16} />
        </span>
        <div>
          <h3 class="text-sm font-semibold">Tampilan</h3>
          <p class="text-[11px] text-base-content/45">Sesuaikan tema aplikasi</p>
        </div>
      </div>

      <div class="mt-5 grid grid-cols-2 gap-3">
        <button
          type="button"
          class="rounded-2xl border-2 p-3 text-left transition-colors {$theme === 'light'
            ? 'border-primary bg-primary/5'
            : 'border-base-content/10 hover:border-base-content/20'}"
          aria-pressed={$theme === 'light'}
          onclick={() => setTheme('light')}
        >
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-2">
            <div class="h-2 w-12 rounded bg-slate-300"></div>
            <div class="mt-2 grid grid-cols-3 gap-1">
              <div class="h-6 rounded bg-white shadow-sm"></div>
              <div class="h-6 rounded bg-white shadow-sm"></div>
              <div class="h-6 rounded bg-emerald-400"></div>
            </div>
          </div>
          <span class="mt-2 flex items-center gap-1.5 text-xs font-medium">
            <Icon name="sun" size={13} /> Terang
          </span>
        </button>

        <button
          type="button"
          class="rounded-2xl border-2 p-3 text-left transition-colors {$theme === 'dark'
            ? 'border-primary bg-primary/5'
            : 'border-base-content/10 hover:border-base-content/20'}"
          aria-pressed={$theme === 'dark'}
          onclick={() => setTheme('dark')}
        >
          <div class="rounded-xl border border-slate-700 bg-slate-900 p-2">
            <div class="h-2 w-12 rounded bg-slate-600"></div>
            <div class="mt-2 grid grid-cols-3 gap-1">
              <div class="h-6 rounded bg-slate-800"></div>
              <div class="h-6 rounded bg-slate-800"></div>
              <div class="h-6 rounded bg-emerald-500"></div>
            </div>
          </div>
          <span class="mt-2 flex items-center gap-1.5 text-xs font-medium">
            <Icon name="moon" size={13} /> Gelap
          </span>
        </button>
      </div>

      <p class="mt-4 text-[11px] leading-relaxed text-base-content/40">
        Preferensi tema disimpan di perangkat ini dan diterapkan sebelum aplikasi dirender agar
        tidak ada kedipan warna.
      </p>
    </section>
  </div>

  <section class="surface p-5">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex items-center gap-2">
        <span class="grid size-8 place-items-center rounded-xl bg-info/12 text-info">
          <Icon name="database" size={16} />
        </span>
        <div>
          <h3 class="text-sm font-semibold">Database MongoDB</h3>
          <p class="text-[11px] text-base-content/45">Koneksi Atlas yang digunakan aplikasi</p>
        </div>
      </div>
      <span class="badge badge-sm gap-1.5 {connected ? 'badge-success' : 'badge-error'}">
        <span class="size-1.5 rounded-full {connected ? 'bg-success-content' : 'bg-error-content'}"
        ></span>
        {connected ? 'Terhubung' : 'Tidak terhubung'}
      </span>
    </div>

    <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-xl bg-base-200/70 p-3">
        <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">
          Database
        </p>
        <p class="mt-1 truncate text-xs font-semibold">{$systemStatus?.db_name ?? '—'}</p>
      </div>
      <div class="rounded-xl bg-base-200/70 p-3">
        <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">Latensi</p>
        <p class="tabular mt-1 text-xs font-semibold">
          {$systemStatus?.db_latency_ms != null ? `${$systemStatus.db_latency_ms} ms` : '—'}
        </p>
      </div>
      <div class="rounded-xl bg-base-200/70 p-3">
        <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">Sumber</p>
        <p class="mt-1 truncate text-xs font-semibold">{sourceLabel}</p>
      </div>
      <div class="rounded-xl bg-base-200/70 p-3">
        <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">
          Folder data
        </p>
        <p class="mt-1 truncate text-xs font-semibold" title={$systemStatus?.data_dir ?? ''}>
          {$systemStatus?.data_dir ?? '—'}
        </p>
      </div>
    </div>

    <div class="mt-3 rounded-xl border border-base-content/8 bg-base-100 p-3">
      <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">
        Connection string aktif (disamarkan)
      </p>
      <p class="mt-1 break-all font-mono text-[11px] text-base-content/60">
        {$systemStatus?.db_uri_masked ?? 'Belum dikonfigurasi'}
      </p>
      {#if $systemStatus?.last_error}
        <p class="mt-2 rounded-lg bg-error/8 px-2 py-1.5 text-[11px] text-error">
          {$systemStatus.last_error}
        </p>
      {/if}
    </div>

    <form class="mt-5 space-y-3" onsubmit={saveConnection}>
      <div class="grid gap-3 sm:grid-cols-[1fr_12rem]">
        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60"
            >Connection string baru</span
          >
          <span
            class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary"
          >
            <Icon name="database" size={15} class="shrink-0 text-base-content/35" />
            <input
              type={showUri ? 'text' : 'password'}
              class="grow border-0 bg-transparent font-mono text-xs outline-none"
              placeholder="mongodb+srv://user:password@cluster…"
              maxlength="2048"
              autocomplete="off"
              spellcheck="false"
              bind:value={uri}
            />
            <button
              type="button"
              class="btn btn-ghost btn-xs btn-circle text-base-content/35"
              aria-label={showUri ? 'Sembunyikan URI' : 'Tampilkan URI'}
              onclick={() => (showUri = !showUri)}
            >
              <Icon name={showUri ? 'eye-off' : 'eye'} size={14} />
            </button>
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Nama database</span>
          <input
            type="text"
            class="input input-bordered w-full font-mono text-xs"
            placeholder="finance_app"
            maxlength="64"
            bind:value={dbName}
            oninput={() => (dbNameEdited = true)}
          />
        </label>
      </div>

      {#if dbError}
        <div class="alert alert-error py-2 text-xs" role="alert">
          <Icon name="alert" size={15} />
          <span>{dbError}</span>
        </div>
      {/if}

      <div class="flex flex-wrap items-center gap-2">
        <button type="submit" class="btn btn-primary btn-sm" disabled={savingDb}>
          {#if savingDb}
            <span class="loading loading-spinner loading-xs"></span>
          {/if}
          Simpan & uji koneksi
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm"
          disabled={$systemLoading}
          onclick={() => void loadSystemStatus()}
        >
          <Icon name="refresh" size={14} />
          Uji ulang
        </button>
        <p class="text-[11px] text-base-content/40">
          Koneksi diuji sebelum disimpan. URI disimpan lokal dengan izin owner-only.
        </p>
      </div>
    </form>
  </section>

  <div class="grid gap-4 lg:grid-cols-2">
    <section class="surface p-5">
      <div class="flex items-center gap-2">
        <span class="grid size-8 place-items-center rounded-xl bg-accent/15 text-accent-content">
          <Icon name="sparkles" size={16} />
        </span>
        <div>
          <h3 class="text-sm font-semibold">Data contoh</h3>
          <p class="text-[11px] text-base-content/45">Isi akun kosong dengan data demo</p>
        </div>
      </div>
      <p class="mt-4 text-xs leading-relaxed text-base-content/50">
        Fitur ini hanya berjalan jika akun belum memiliki dompet. Data contoh berguna untuk mencoba
        grafik dan filter tanpa memasukkan transaksi satu per satu.
      </p>
      <button
        type="button"
        class="btn btn-ghost btn-sm mt-4"
        disabled={seeding || $wallets.length > 0}
        onclick={seedDemo}
      >
        {#if seeding}
          <span class="loading loading-spinner loading-xs"></span>
        {:else}
          <Icon name="sparkles" size={15} />
        {/if}
        Muat data contoh
      </button>
      {#if $wallets.length > 0}
        <p class="mt-2 text-[11px] text-base-content/40">
          Tidak tersedia karena akun sudah memiliki dompet.
        </p>
      {/if}
    </section>

    <section class="surface p-5">
      <div class="flex items-center gap-2">
        <span class="grid size-8 place-items-center rounded-xl bg-base-200 text-base-content/55">
          <Icon name="chart" size={16} />
        </span>
        <div>
          <h3 class="text-sm font-semibold">Tentang aplikasi</h3>
          <p class="text-[11px] text-base-content/45">Informasi versi dan runtime</p>
        </div>
      </div>
      <dl class="mt-4 space-y-2 text-xs">
        <div class="flex justify-between gap-4">
          <dt class="text-base-content/45">FinanceApp</dt>
          <dd class="font-medium">{$systemStatus?.app_version ?? '0.1.0'}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-base-content/45">Python</dt>
          <dd class="font-medium">{$systemStatus?.python_version ?? '—'}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-base-content/45">Frontend</dt>
          <dd class="font-medium">SvelteKit + Svelte 5</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-base-content/45">Shell</dt>
          <dd class="font-medium">Tauri 2 + PyTauri</dd>
        </div>
      </dl>
      <div class="alert alert-info mt-4 py-2 text-[11px]">
        <Icon name="lock" size={14} />
        <span>
          JWT secret dibuat unik per instalasi dan disimpan lokal. Jangan bagikan connection string
          MongoDB Anda.
        </span>
      </div>
    </section>
  </div>
</div>
