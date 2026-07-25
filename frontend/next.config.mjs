/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // O navegador fala com o Next; o Next repassa para o FastAPI. Assim não há CORS
  // em produção e o backend não precisa ficar exposto na internet.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://127.0.0.1:8077"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
