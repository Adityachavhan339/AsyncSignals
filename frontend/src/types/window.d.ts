interface Window {
  ethereum?: {
    request: (args: { method: string; params?: any[] }) => Promise<any>;
  };
  solana?: {
    isPhantom?: boolean;
    connect: () => Promise<{ publicKey: { toString: () => string } }>;
    signMessage: (message: Uint8Array, encoding: string) => Promise<{ signature: Uint8Array }>;
  };
}
