"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Zap, AlertTriangle, Globe, Wallet, Ghost, Hexagon } from "lucide-react";
import { SiweMessage } from "siwe";

export default function SignInPage() {
  const [error, setError] = useState("");
  const [siweLoading, setSiweLoading] = useState(false);
  const [siwsLoading, setSiwsLoading] = useState(false);
  const [siwbLoading, setSiwbLoading] = useState(false);
  const router = useRouter();

  const handleSiwe = async () => {
    setSiweLoading(true);
    setError("");

    try {
      if (!window.ethereum) {
        setError("MetaMask not detected. Please install MetaMask extension.");
        setSiweLoading(false);
        return;
      }

      const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
      const address = accounts[0];

      const nonce = Math.random().toString(36).substring(2, 15);
      
      const siweMessage = new SiweMessage({
        domain: window.location.host,
        address: address,
        statement: "Sign in to AsyncSignals Mission Control",
        uri: window.location.origin,
        version: "1",
        chainId: 1,
        nonce: nonce,
      });

      const messageToSign = siweMessage.prepareMessage();

      const signature = await window.ethereum.request({
        method: "personal_sign",
        params: [messageToSign, address],
      });

      const result = await signIn("siwe", {
        message: JSON.stringify(siweMessage),
        signature,
        redirect: false,
        callbackUrl: "/",
      });

      if (result?.error) {
        setError("Ethereum wallet authentication failed");
        setSiweLoading(false);
      } else {
        router.push("/");
        router.refresh();
      }
    } catch (e) {
      console.error("SIWE error:", e);
      setError("Ethereum wallet connection failed");
      setSiweLoading(false);
    }
  };

  const handleSiws = async () => {
    setSiwsLoading(true);
    setError("");

    try {
      // Check if Phantom is installed
      const provider = (window as any).solana;
      if (!provider || !provider.isPhantom) {
        setError("Phantom wallet not detected. Please install Phantom extension.");
        setSiwsLoading(false);
        return;
      }

      // Connect to Phantom
      const response = await provider.connect();
      const publicKey = response.publicKey.toString();

      // Create message
      const nonce = Math.random().toString(36).substring(2, 15);
      const message = `AsyncSignals Mission Control\nSign in with Solana\nAddress: ${publicKey}\nNonce: ${nonce}\nURI: ${window.location.origin}`;

      // Sign message
      const encodedMessage = new TextEncoder().encode(message);
      const signedMessage = await provider.signMessage(encodedMessage, "utf8");
      const signature = Buffer.from(signedMessage.signature).toString("base64");

      // Verify with NextAuth
      const result = await signIn("siws", {
        message: message,
        signature: signature,
        publicKey: publicKey,
        redirect: false,
        callbackUrl: "/",
      });

      if (result?.error) {
        setError("Solana wallet authentication failed");
        setSiwsLoading(false);
      } else {
        router.push("/");
        router.refresh();
      }
    } catch (e) {
      console.error("SIWS error:", e);
      setError("Solana wallet connection failed");
      setSiwsLoading(false);
    }
  };

  const handleSiwb = async () => {
    setSiwbLoading(true);
    setError("");

    try {
      if (!window.ethereum) {
        setError("Coinbase Wallet or MetaMask not detected.");
        setSiwbLoading(false);
        return;
      }

      const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
      const address = accounts[0];

      const nonce = Math.random().toString(36).substring(2, 15);
      
      const siweMessage = new SiweMessage({
        domain: window.location.host,
        address: address,
        statement: "Sign in to AsyncSignals Base L2",
        uri: window.location.origin,
        version: "1",
        chainId: 8453, // Base chain ID
        nonce: nonce,
      });

      const messageToSign = siweMessage.prepareMessage();

      const signature = await window.ethereum.request({
        method: "personal_sign",
        params: [messageToSign, address],
      });

      const result = await signIn("siwb", {
        message: JSON.stringify(siweMessage),
        signature,
        redirect: false,
        callbackUrl: "/",
      });

      if (result?.error) {
        setError("Base wallet authentication failed");
        setSiwbLoading(false);
      } else {
        router.push("/");
        router.refresh();
      }
    } catch (e) {
      console.error("SIWB error:", e);
      setError("Base wallet connection failed");
      setSiwbLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-[#06111a] to-[#09131c]">
      <div className="w-full max-w-md p-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-emerald-400 text-[#051018] font-bold text-xl mb-4">
            <Zap size={20} />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">AsyncSignals</h1>
          <p className="text-sm text-slate-400">Multi-chain telemetry infrastructure</p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0d1722] p-6 shadow-2xl space-y-3">
          <h2 className="text-lg font-bold text-white mb-2">Sign In</h2>
          
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <AlertTriangle size={14} className="text-rose-400" />
              <span className="text-xs text-rose-400">{error}</span>
            </div>
          )}

          {/* Google OAuth */}
          <button
            onClick={() => signIn("google", { callbackUrl: "/" })}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-white/5 text-white border border-white/10 hover:bg-white/10 transition-colors"
          >
            <Globe size={16} />
            Sign in with Google
          </button>

          {/* SIWE - MetaMask */}
          <button
            onClick={handleSiwe}
            disabled={siweLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-orange-500/20 text-orange-400 border border-orange-500/20 hover:bg-orange-500/30 disabled:opacity-50 transition-colors"
          >
            <Wallet size={16} />
            {siweLoading ? "Connecting..." : "Sign in with MetaMask"}
          </button>

          {/* SIWS - Phantom / Solana */}
          <button
            onClick={handleSiws}
            disabled={siwsLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/20 hover:bg-purple-500/30 disabled:opacity-50 transition-colors"
          >
            <Ghost size={16} />
            {siwsLoading ? "Connecting..." : "Sign in with Phantom"}
          </button>

          {/* SIWB - Base / Coinbase */}
          <button
            onClick={handleSiwb}
            disabled={siwbLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/20 hover:bg-blue-500/30 disabled:opacity-50 transition-colors"
          >
            <Hexagon size={16} />
            {siwbLoading ? "Connecting..." : "Sign in with Base"}
          </button>

          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <p className="text-xs text-slate-500 text-center">
              Web2 + Web3 Multi-Chain Authentication
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
