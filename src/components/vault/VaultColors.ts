function hashToIndex(s: string, mod: number) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % mod;
}

const VAULT_COLORS = [
  "vaultColor-0",
  "vaultColor-1",
  "vaultColor-2",
  "vaultColor-3",
  "vaultColor-4",
  "vaultColor-5",
  "vaultColor-6",
  "vaultColor-7",
];

export function colorClassForVaultId(vaultId: string) {
  return VAULT_COLORS[hashToIndex(vaultId, VAULT_COLORS.length)];
}
