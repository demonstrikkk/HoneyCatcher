import React, { useLayoutEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import {
    Shield,
    Mic,
    Zap,
    Cpu,
    ChevronRight,
    Lock,
    Eye,
    Terminal,
    Play,
    Activity,
    Layers,
    Binary
} from 'lucide-react';
import { motion } from 'framer-motion';
import logo from '../assets/logo.png';

gsap.registerPlugin(ScrollTrigger);

const LandingPage = () => {
    const navigate = useNavigate();
    const containerRef = useRef();
    const horizontalSectionRef = useRef();
    const heroContentRef = useRef();
    const heroZoomRef = useRef();

    useLayoutEffect(() => {
        let ctx = gsap.context(() => {
            // Hero Zoom Effect
            gsap.fromTo(heroZoomRef.current,
                { scale: 1.5, opacity: 0 },
                { scale: 1, opacity: 1, duration: 2, ease: "power4.out" }
            );

            gsap.fromTo(heroContentRef.current,
                { y: 100, opacity: 0 },
                { y: 0, opacity: 1, duration: 1.5, delay: 0.5, ease: "power4.out" }
            );

            // Horizontal Scroll Section
            const sections = horizontalSectionRef.current.querySelectorAll('.panel');
            gsap.to(sections, {
                xPercent: -100 * (sections.length - 1),
                ease: "none",
                scrollTrigger: {
                    trigger: horizontalSectionRef.current,
                    pin: true,
                    scrub: 1,
                    snap: 1 / (sections.length - 1),
                    end: () => "+=" + horizontalSectionRef.current.offsetWidth
                }
            });

            // Parallax sections
            gsap.utils.toArray('.gsap-fade-in').forEach((el) => {
                gsap.from(el, {
                    y: 60,
                    opacity: 0,
                    duration: 1.2,
                    ease: "power3.out",
                    scrollTrigger: {
                        trigger: el,
                        start: "top 85%",
                        toggleActions: "play none none reverse"
                    }
                });
            });
        }, containerRef);

        return () => ctx.revert();
    }, []);

    const features = [
        {
            title: "Autonomous Interception",
            desc: "AI-driven honeypots that engage scammers in real-time, extracting tactical intelligence without human intervention.",
            icon: Shield,
            stat: "99.9% BLOCK RATE",
            color: "emerald"
        },
        {
            title: "Acoustic Naturalization",
            desc: "Advanced neural speech synthesis that adds human-like fillers, hesitations, and regional dialects to stall threat actors.",
            icon: Mic,
            stat: "<200MS LATENCY",
            color: "teal"
        },
        {
            title: "Intelligence Extraction",
            desc: "Deep packet inspection for voice calls. Automatically identifying UPI IDs, Bank Accounts, and behavioral tactics.",
            icon: Binary,
            stat: "REAL-TIME INTEL",
            color: "emerald"
        }
    ];

    return (
        <div ref={containerRef} className="bg-black text-white selection:bg-emerald-500/30 overflow-x-hidden font-sans antialiased">

            {/* Immersive Background */}
            <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 -left-[10%] w-[60%] h-[60%] bg-emerald-500/10 blur-[160px] rounded-full mix-blend-screen opacity-50" />
                <div className="absolute bottom-0 -right-[10%] w-[60%] h-[60%] bg-teal-500/5 blur-[160px] rounded-full mix-blend-screen opacity-50" />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
                <div className="absolute inset-0 bg-[#020617] -z-10" />
            </div>

            {/* Navigation */}
            <nav className="fixed top-0 left-0 w-full z-50 px-10 py-8 flex justify-between items-center bg-gradient-to-b from-black/80 to-transparent backdrop-blur-sm">
                <div className="flex items-center gap-3">
                    <img src={logo} alt="HoneyBadger Logo" className="w-10 h-10 object-contain drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                    <span className="text-xl font-black tracking-tighter uppercase italic">Honey<span className="text-emerald-500">Badger</span></span>
                </div>
                <div className="flex items-center gap-10">
                    <a href="#features" className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 hover:text-emerald-400 transition-colors">Tactical Edge</a>
                    <a href="#intel" className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 hover:text-emerald-400 transition-colors">Intelligence</a>
                    <button
                        onClick={() => navigate('/voice')}
                        className="px-6 py-2.5 bg-emerald-600/10 border border-emerald-500/30 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] text-emerald-400 hover:bg-emerald-500 hover:text-white transition-all duration-300"
                    >
                        Terminal Login
                    </button>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative h-screen flex items-center justify-center px-6 overflow-hidden">
                <div ref={heroZoomRef} className="absolute inset-0 flex items-center justify-center">
                    <div className="relative w-[1200px] h-[1200px] flex items-center justify-center">
                        <div className="absolute inset-0 border-[1px] border-emerald-500/10 rounded-full animate-[spin_20s_linear_infinite]" />
                        <div className="absolute inset-[20%] border-[2px] border-emerald-500/5 rounded-full animate-[spin_15s_linear_infinite_reverse]" />
                        <div className="absolute inset-[40%] border-[1px] border-emerald-500/20 rounded-full" />
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(16,185,129,0.15)_0%,transparent_70%)]" />

                        {/* Central Logo Motif */}
                        <motion.div
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 0.3 }}
                            transition={{ duration: 2, ease: "easeOut" }}
                            className="relative w-96 h-96 opacity-30 blur-sm grayscale hover:grayscale-0 hover:opacity-50 hover:blur-none transition-all duration-1000"
                        >
                            <img src={logo} alt="Background Logo" className="w-full h-full object-contain" />
                        </motion.div>
                    </div>
                </div>

                <div ref={heroContentRef} className="relative z-10 text-center max-w-5xl mx-auto">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-8">
                        <Lock className="w-3 h-3" />
                        <span className="text-[10px] font-black uppercase tracking-[0.3em]">Quantum Defended Honeypot</span>
                    </div>
                    <h1 className="text-7xl md:text-9xl font-black tracking-tighter leading-none mb-8">
                        INTERCEPTING THE <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-600">UNTOUCHABLES.</span>
                    </h1>
                    <p className="text-xl md:text-2xl text-slate-400 font-medium max-w-2xl mx-auto leading-relaxed mb-12">
                        HoneyBadger deploys cinematic AI actors to engage, exhaust, and unmask digital threat actors in real-time.
                    </p>
                    <div className="flex flex-col md:flex-row items-center justify-center gap-6">
                        <button
                            onClick={() => navigate('/voice')}
                            className="group relative px-10 py-5 bg-emerald-600 rounded-2xl overflow-hidden transition-all duration-500 hover:bg-emerald-500 hover:scale-105"
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                            <div className="relative flex items-center gap-3">
                                <span className="text-sm font-black uppercase tracking-widest text-white">Deploy Initial Vector</span>
                                <ChevronRight className="w-4 h-4 text-white group-hover:translate-x-1 transition-transform" />
                            </div>
                        </button>
                        <button className="flex items-center gap-3 px-10 py-5 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-white/10 transition-all">
                            <Play className="w-4 h-4 fill-white" /> Watch Interception
                        </button>
                    </div>
                </div>

                <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-4 text-slate-500">
                    <span className="text-[10px] font-black uppercase tracking-[0.5em]">Scroll to Decode</span>
                    <div className="w-[1px] h-20 bg-gradient-to-b from-emerald-500 to-transparent" />
                </div>
            </section>

            {/* Horizontal Scroll Features */}
            <section ref={horizontalSectionRef} id="features" className="h-screen bg-[#010411] flex overflow-hidden">
                <div className="panel min-w-full h-screen flex items-center justify-center px-20">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center max-w-7xl">
                        <div>
                            <div className="w-16 h-1 bg-emerald-500 mb-8" />
                            <h2 className="text-6xl font-black tracking-tighter mb-8 italic">THE TACTICAL <br /> <span className="text-emerald-500">ADVANTAGE</span></h2>
                            <p className="text-lg text-slate-400 leading-relaxed max-w-md">
                                Traditional security reacts. HoneyBadger pro-actively mimics weak vectors to draw in threats, systematically extracting identifiers that lead directly to neutralization.
                            </p>
                        </div>
                        <div className="relative aspect-square">
                            <div className="absolute inset-0 bg-emerald-500/20 blur-[100px] rounded-full animate-pulse" />
                            <div className="relative h-full bg-slate-900/50 backdrop-blur-3xl border border-white/5 rounded-[4rem] overflow-hidden p-12 flex flex-col justify-center gap-8 shadow-3xl">
                                <div className="flex items-center justify-between border-b border-white/10 pb-6">
                                    <div className="flex flex-col">
                                        <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Signal Strength</span>
                                        <span className="text-2xl font-black font-mono tracking-tighter text-white">100.0%</span>
                                    </div>
                                    <Activity className="w-8 h-8 text-emerald-500 animate-pulse" />
                                </div>
                                <div className="space-y-4">
                                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div initial={{ width: 0 }} whileInView={{ width: '85%' }} className="h-full bg-emerald-500" />
                                    </div>
                                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div initial={{ width: 0 }} whileInView={{ width: '60%' }} transition={{ delay: 0.2 }} className="h-full bg-teal-500" />
                                    </div>
                                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div initial={{ width: 0 }} whileInView={{ width: '95%' }} transition={{ delay: 0.4 }} className="h-full bg-emerald-400" />
                                    </div>
                                </div>
                                <div className="p-4 bg-black/40 rounded-2xl border border-white/5 font-mono text-[10px] text-emerald-400/70">
                                    {"> "} INITIALIZING_HONEYPOT_PROTOCOL...<br />
                                    {"> "} DETECTING_INCOMING_VECTOR...<br />
                                    {"> "} INTERCEPTION_ACTIVE_STABLE
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Panel 2: Acoustic Analysis */}
                <div className="panel min-w-full h-screen flex items-center justify-center bg-black/50 px-20 relative overflow-hidden">
                    <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:20px_20px]" />
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center max-w-7xl z-10">
                        <div className="order-2 lg:order-1 relative h-[500px] w-full bg-slate-900/40 backdrop-blur-3xl border border-white/5 rounded-[3rem] p-10 shadow-3xl">
                            <div className="flex items-center gap-3 mb-10">
                                <div className="w-10 h-10 rounded-xl bg-emerald-600/20 flex items-center justify-center text-emerald-400">
                                    <Mic className="w-5 h-5" />
                                </div>
                                <span className="text-[10px] font-black uppercase tracking-[0.4em] text-emerald-500">Neural Acoustic Lab</span>
                            </div>
                            <div className="space-y-8">
                                <div className="flex items-end gap-1 h-32 justify-center">
                                    {[...Array(30)].map((_, i) => (
                                        <motion.div
                                            key={i}
                                            animate={{ height: [20, Math.random() * 80 + 20, 20] }}
                                            transition={{ repeat: Infinity, duration: 1.5, delay: i * 0.05 }}
                                            className="w-1.5 bg-emerald-500/50 rounded-full"
                                        />
                                    ))}
                                </div>
                                <div className="p-6 bg-black/40 rounded-2xl border border-white/5 text-sm italic text-emerald-100 font-medium leading-relaxed">
                                    "Wait... um, I mean... I'm not really sure if I can do that right now. Actually, could you possibly explain that again? I'm a bit confused."
                                </div>
                                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">
                                    <span>Entropy Level</span>
                                    <span className="text-emerald-400">High Authenticity</span>
                                </div>
                            </div>
                        </div>
                        <div className="order-1 lg:order-2">
                            <h2 className="text-6xl font-black tracking-tighter mb-8 italic uppercase">NATIVE <br /> <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-teal-400 font-black">NATURALIZATION</span></h2>
                            <p className="text-lg text-slate-400 leading-relaxed max-w-md">
                                Our SLM (Small Language Models) convert robotic AI logic into authentic spoken language, adding human fillers, stammers, and emotional triggers that keep scammers hooked until they reveal their final payloads.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Panel 3: Global Intel */}
                <div className="panel min-w-full h-screen flex items-center justify-center px-20">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center max-w-7xl">
                        <div>
                            <h2 className="text-6xl font-black tracking-tighter mb-8 italic uppercase">DEEP <br /> <span className="text-emerald-500">INTEL</span> ANALYSIS</h2>
                            <p className="text-lg text-slate-400 leading-relaxed max-w-md mb-8">
                                Every interaction is parsed for actionable data. Bank branches, UPI handles, and payment links are extracted, validated, and reported to relevant authorities automatically.
                            </p>
                            <button
                                onClick={() => navigate('/voice')}
                                className="px-10 py-5 border-[2px] border-emerald-500 rounded-2xl text-sm font-black uppercase tracking-widest text-emerald-500 hover:bg-emerald-500 hover:text-white transition-all duration-500 shadow-[0_0_30px_rgba(16,185,129,0.2)]"
                            >
                                Access Intel Terminal
                            </button>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="p-8 bg-slate-900/30 backdrop-blur-xl border border-white/5 rounded-3xl hover:border-emerald-500/30 transition-all duration-500 group">
                                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-6 group-hover:scale-110 transition-transform">
                                        <Cpu className="w-6 h-6" />
                                    </div>
                                    <div className="text-3xl font-black tracking-tighter mb-2 italic">1.2M+</div>
                                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">Vector Analysis</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* Cinematic Stats Section */}
            <section id="intel" className="py-32 px-6 relative bg-black">
                <div className="max-w-7xl mx-auto gsap-fade-in">
                    <div className="text-center mb-24">
                        <h2 className="text-4xl md:text-6xl font-black tracking-tighter italic uppercase mb-6">GLOBAL THREAT <span className="text-emerald-500">OVERVIEW</span></h2>
                        <p className="text-slate-400 max-w-xl mx-auto">Real-time status of current honeypot deployments and extraction metrics.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {features.map((feature, i) => (
                            <div key={i} className="relative p-10 bg-slate-900/20 backdrop-blur-3xl border border-white/5 rounded-[3rem] overflow-hidden group hover:border-emerald-500/20 transition-all duration-500 h-full flex flex-col">
                                <div className="absolute top-0 right-0 p-8">
                                    <feature.icon className="w-12 h-12 text-emerald-500/10 group-hover:text-emerald-500/30 transition-colors" />
                                </div>
                                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-8">
                                    <feature.icon className="w-6 h-6" />
                                </div>
                                <h3 className="text-2xl font-black tracking-tighter mb-4 italic uppercase">{feature.title}</h3>
                                <p className="text-slate-400 leading-relaxed mb-auto pb-8">
                                    {feature.desc}
                                </p>
                                <div className="pt-8 border-t border-white/5 flex items-center justify-between">
                                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-500 italic">Target Metric</span>
                                    <span className="text-xl font-black font-mono tracking-tighter text-white">{feature.stat}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Final CTA */}
            <section className="py-40 px-6 relative overflow-hidden flex items-center justify-center bg-black">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-emerald-500/5 blur-[120px] rounded-full pointer-events-none" />

                <div className="max-w-4xl mx-auto text-center relative z-10 gsap-fade-in">
                    <h2 className="text-6xl md:text-8xl font-black tracking-tighter italic uppercase mb-10 leading-none">READY TO DEPLOY <br /> <span className="text-emerald-500">THE BADGER?</span></h2>
                    <p className="text-xl text-slate-400 mb-12 max-w-xl mx-auto">Join the decentralized defense network and turn every scam call into a tactical failure.</p>
                    <button
                        onClick={() => navigate('/voice')}
                        className="group relative px-12 py-6 bg-emerald-600 rounded-[2rem] overflow-hidden transition-all duration-500 hover:bg-emerald-500 hover:scale-110 shadow-[0_0_50px_rgba(16,185,129,0.3)] hover:shadow-[0_0_70px_rgba(16,185,129,0.5)]"
                    >
                        <div className="relative flex items-center gap-4">
                            <span className="text-lg font-black uppercase tracking-[0.2em] text-white">Initialize Vector Access</span>
                            <Zap className="w-5 h-5 text-white animate-pulse" />
                        </div>
                    </button>

                    <div className="mt-20 flex justify-center gap-12 grayscale opacity-40 hover:grayscale-0 hover:opacity-100 transition-all duration-700">
                        <div className="flex items-center gap-2">
                            <div className="h-1.5 w-12 bg-slate-800 rounded-full" />
                            <span className="text-[8px] font-black uppercase tracking-[0.3em] text-slate-600">Secure Uplink</span>
                        </div>
                        <div className="flex items-center gap-2 text-emerald-500">
                            <div className="h-1.5 w-12 bg-emerald-900 rounded-full" />
                            <span className="text-[8px] font-black uppercase tracking-[0.3em] text-emerald-500 animate-pulse italic">Interception Active</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-20 px-10 border-t border-white/5 bg-black/40 backdrop-blur-3xl relative z-10">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-10">
                    <div className="flex items-center gap-3">
                        <img src={logo} alt="HoneyBadger Logo" className="w-8 h-8 object-contain opacity-70" />
                        <span className="font-black tracking-tighter uppercase italic text-sm">Honey<span className="text-emerald-500">Badger</span> v2.0 Tactical</span>
                    </div>
                    <div className="flex gap-10">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">Privacy Protocol</span>
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">Security Audit</span>
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">Intel Access</span>
                    </div>
                    <div className="text-[10px] font-black font-mono text-slate-700">
                        © 2026 HONEYBADGER_DEFENSE_CORP // DEPLOY_STABLE
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default LandingPage;
