<script lang="ts">
  import { centsToInput, formatNumber, parseAmountToCents } from '$lib/utils/format';

  let {
    value = $bindable(0),
    currency = 'IDR',
    placeholder = '0',
    disabled = false,
    large = false,
    id = 'money-input'
  }: {
    value?: number;
    currency?: string;
    placeholder?: string;
    disabled?: boolean;
    large?: boolean;
    id?: string;
  } = $props();

  let display = $state(centsToInput(value));
  let focused = $state(false);

  $effect(() => {
    if (!focused) display = centsToInput(value);
  });

  function handleInput(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const cents = parseAmountToCents(input.value);
    value = cents;
    display = cents ? formatNumber(cents / 100) : '';
  }

  const prefix = $derived(currency === 'IDR' ? 'Rp' : currency);
</script>

<label
  class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary {large
    ? 'input-lg h-14'
    : ''}"
  for={id}
>
  <span class="shrink-0 text-sm font-semibold text-base-content/45">{prefix}</span>
  <input
    {id}
    class="tabular min-w-0 grow border-0 bg-transparent p-0 text-right text-base font-semibold outline-none focus:outline-none {large
      ? 'text-2xl'
      : ''}"
    type="text"
    inputmode="numeric"
    autocomplete="off"
    {placeholder}
    {disabled}
    value={display}
    oninput={handleInput}
    onfocus={() => (focused = true)}
    onblur={() => {
      focused = false;
      display = centsToInput(value);
    }}
  />
</label>
