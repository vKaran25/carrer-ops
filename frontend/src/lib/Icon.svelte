<script lang="ts">
  export let name = 'search'; export let size = 20;
  const paths: Record<string, string> = {
    search: 'M21 21l-4.3-4.3M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
    board: 'M3 4h5v16H3zM10 4h5v10h-5zM17 4h4v13h-4z',
    file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5',
    settings: 'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2',
    arrow: 'M5 12h14M13 6l6 6-6 6', close: 'M6 6l12 12M6 18 18 6',
    pin: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM12 7a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z',
    external: 'M14 3h7v7M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5',
    check: 'M5 12l4 4L19 6', upload: 'M12 16V3M7 8l5-5 5 5M3 16v5h18v-5',
    sparkle: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z',
    list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
    briefcase: 'M9 6V3h6v3M3 6h18v14H3zM3 11l9 3 9-3M12 12v4',
    info: 'M12 11v6M12 7h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
    plus: 'M12 5v14M5 12h14', clock: 'M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
    download: 'M12 3v13M7 11l5 5 5-5M3 17v4h18v-4'
  };
</script>
<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={paths[name] || paths.file}/></svg>
