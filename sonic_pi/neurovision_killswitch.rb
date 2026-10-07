use_bpm 100

set :d1, 0 # 1.simple beat
set :d2, 0 # 2.fast hi hats beat with tss noise
set :d3, 0 # 3. very fast hi hats
set :d4, 0 # 4. basic pop punk drum beat
set :b1, 0 # 5. groovy bass
set :b2, 0 # 6. travis scott type bass
set :b3, 0 # 7. bass guitar
set :b4, 0 # 8. bass guitar follow snare and bass drum
set :p1, 0 # 9. main melody
set :p2, 0 # 10. additional melody
set :p3, 0 # 11. distorted a piano to sound like a guitar but i can change it
set :p4, 0 # 12. TBC (another melody)
set :e1, 0 # 13. harmonising violins sound
set :e2, 0 # 14. reggae guitar
set :e3, 0 # 15. guitar solo
set :e4, 0 # 16. sustained drone note ambience (had some synthy line going over the top but it got annoying)


live_loop :osc_router do
  use_real_time
  msg = sync "/osc*/loop/only"
  choice = msg[0].to_i
  
  case choice
  when 1
    set :d1, 1
  when 11
    set :d1, 0
  when 2
    set :d2, 1
  when 22
    set :d2, 0
  when 3
    set :d3, 1
  when 33
    set :d3, 0
  when 4
    set :d4, 1
  when 44
    set :d4, 0
  when 5
    set :b1, 1
  when 55
    set :b1, 0
  when 6
    set :b2, 1
  when 66
    set :b2, 0
  when 7
    set :b3, 1
  when 77
    set :b3, 0
  when 8
    set :b4, 1
  when 88
    set :b4, 0
  when 9
    set :p1, 1
  when 99
    set :p1, 0
  when 10
    set :p2, 1
  when 1010
    set :p2, 0
  when 110
    set :p3, 1
  when 1111
    set :p3, 0
  when 12
    set :p3, 1 #ran out of space change to p4 if added
  when 1212
    set :p3, 0 #ran out of space change to p4 if added
  when 13
    set :e1, 1
  when 1313
    set :e1, 0
  when 14
    set :e2, 1
  when 1414
    set :e2, 0
  when 15
    set :e3, 1
  when 1515
    set :e3, 0
  when 16
    set :e4, 1
  when 1616
    set :e4, 0
  when 6969
    [:d1,:d2,:d3,:d4,:b1,:b2,:b3,:b4,:p1,:p2,:p3,:p4,:e1,:e2,:e3,:e4].each do |k|
      set k, 0
    end
  else
    puts "Unknown /loop/only value:", choice
  end
end

# D1
live_loop :d1hats do
  sample :drum_cymbal_closed, amp: get(:d1); sleep 0.5
end
live_loop :d1kick do
  sample :bd_tek, amp: get(:d1); sleep 2; sample :bd_tek, amp: get(:d1); sleep 2
end
live_loop :d1snare do
  sleep 1; sample :drum_snare_soft, amp: get(:d1); sleep 2; sample :drum_snare_soft, amp: get(:d1); sleep 1
end

# D2
live_loop :d2hats do
  8.times do
    sample :drum_cymbal_closed, amp: get(:d2); sleep 0.25
end end
live_loop :d2snare do
  sleep 1; sample :drum_snare_hard, amp: get(:d2); sleep 1
end
live_loop :d2kick do
  sample :bd_tek, amp: get(:d2); sleep 0.75; sample :bd_tek, amp: get(:d2); sleep 0.25; sleep 1
end
live_loop :tss do
  sleep 3.5; sample :drum_cymbal_open, amp: get(:d2), sustain: 0, release: 0.12; sleep 0.5
end

# D3
live_loop :d3hats do
  sample :drum_cymbal_closed, amp: get(:d3); sleep 0.25
end
live_loop :d3kick do
  sample :bd_tek, amp: get(:d3); sleep 4
end
live_loop :d3snare do
  sleep 1; sample :drum_snare_soft, amp: get(:d3); sleep 2; sample :drum_snare_soft, amp: get(:d1); sleep 1
end

# D4
live_loop :d4hats do
  2.times do
    sample :drum_cymbal_closed, amp: get(:d1); sleep 0.5
end end
live_loop :d4kick do
  2.times do
    sample :bd_jazz, amp: get(:d4)*3; sleep 1.25; sample :bd_jazz, amp: get(:d4)*3; sleep 0.75
end end
live_loop :d4snare do
  2.times do
    sleep 0.5; sample :drum_snare_hard, amp: get(:d4); sleep 0.5
end end

# B1
use_synth :bass_foundation
step = 0.25
pattern = "xxxx----".chars
prog12 = (ring :c2, :g1, :a1, :f1, :c2, :g1, :a1, :f1,:c2, :g1, :a1, :f1)
i = 0
live_loop :b1bass do
  4.times do
    root = prog12.tick(:chords)
    16.times do |s|
      if pattern[s % 8] == "x"
        note_to_play = i.even? ? root : root + 7; play note_to_play, release: step * 0.9, amp: get(:b1)
        i += 1
      end
      sleep step
end end end

# B2
live_loop :b2bass do
  use_synth :sine
  2.times do
    root = prog12.tick(:b2roots)
    with_fx :distortion, distort: 0.6 do
      with_fx :lpf, cutoff: 70 do
        play root, sustain: 2.75, release: 0.6, amp: get(:b2); sleep 4
end end end end

# B3
live_loop :b3bass do
  use_synth :bass_foundation
  4.times do
    root = prog12.tick(:b3roots)
    with_fx :lpf, cutoff: 70 do
      16.times do
        play root, sustain: 0.1, release: 0.4, amp: get(:b3)
        sleep 0.25
end end end end

# B4
bassprog = (ring :c2, :g1, :a1, :f1,)
live_loop :b4bass do
  use_synth :bass_foundation
  4.times do
    root = bassprog.tick(:b4roots)
    with_fx :lpf, cutoff: 70 do
      2.times do
        play root, sustain: 0.1, release: 0.4, amp: get(:b4); sleep 0.5
        play root, sustain: 0.1, release: 0.4, amp: get(:b4);sleep 0.75
        play root, sustain: 0.1, release: 0.4, amp: get(:b4);sleep 0.25
        play root, sustain: 0.1, release: 0.4, amp: get(:b4);sleep 0.5
end end end end

# P1
use_synth :piano
melody_durs = [0.75,0.75,1,0.5,0.5,0.5]
orig_phrases = [
  {n:[:c5,:g4,:c5,:g4,:c5,:g4], b: :c4, ch: chord(:c3,:major)},
  {n:[:b4,:g4,:b4,:g4,:b4,:g4], b: :g3, ch: chord(:g3,:major)},
  {n:[:a4,:g4,:a4,:g4,:a4,:g4], b: :a3, ch: chord(:a3,:minor)},
  {n:[:a4,:g4,:a4,:g4,:a4,:g4], b: :f3, ch: chord(:f3,:major)}
]
define(:pulse4){|x,a| in_thread{4.times{play x,sustain:0.8,release:0.2,amp: get(:p1); sleep 1}}}
define(:play_orig_4bars){|with_chords=false|
  orig_phrases.each do |p|
    pulse4 p[:b], get(:p1)
    pulse4 p[:ch], get(:p1) if with_chords
    play_pattern_timed p[:n], melody_durs, release: 0.2, amp: get(:p1)
  end
}
live_loop(:p1piano) do
  2.times{ play_orig_4bars false }
  play_orig_4bars true
end

# p2
live_loop(:p2piano) do
  use_synth :piano
  
  durs = (ring 0.5,0.5,1,0.5,0.5,1)
  bars = [
    [:e5,:d5,:c5,:g4,:e5,:c5], [:d5,:b4,:g4,:a4,:b4,:d5],
    [:c5,:a4,:e5,:d5,:c5,:a4], [:c5,:a4,:f4,:g4,:a4,:c5],
    [:e5,:d5,:c5,:g4,:e5,:c5], [:d5,:b4,:g4,:a4,:b4,:d5],
    [:c5,:a4,:e5,:d5,:c5,:a4], [:c5,:a4,:f4,:g4,:a4,:c5],
    [:g5,:e5,:c5,:d5,:e5,:g5], [:fs5,:d5,:b4,:a4,:b4,:d5],
    [:e5,:c5,:a4,:b4,:c5,:e5], [:f5,:e5,:c5,:a4,:g4,:a4]
  ]
  bars.each { |n| play_pattern_timed n, durs, release: 0.25, amp: get(:p2) }
end

#p3
live_loop :p3piano do
  use_synth :piano
  with_fx :distortion, distort:0.2 do
    4.times do
      root = prog12.tick(:p3roots)
      with_fx :lpf, cutoff: 70 do
        16.times do
          play [root + 12, root + 19], sustain: 0.2, release: 0.2, attack: 0.01, amp: get(:p3)
          sleep 0.25
end end end end end

# e1
live_loop(:violins_e1) do
  use_synth :blade
  use_synth_defaults attack:0.02, sustain:0.2, release:0.25
  with_fx(:reverb, room:0.9, mix:0.35) do
    with_fx(:lpf, cutoff:115) do
      12.times do
        fifth = case prog12.tick(:vroots)
        when :c2 then :g5
        when :g1 then :d6
        when :a1 then :e6
        when :f1 then :c6
        end
        play fifth, sustain:3.2, release:0.6, amp:get(:e1)
        sleep 4
end end end end

# e2 off beat reggae
live_loop :reggae do
  use_synth :dsaw
  use_synth_defaults attack: 0.003, sustain: 0.0, release: 0.09, amp: get(:e2)
  with_fx :distortion, distort: 0.85 do
    with_fx :compressor, threshold: 0.35, slope_above: 0.25 do
      with_fx :hpf, cutoff: 95 do
        with_fx :lpf, cutoff: 100 do
          
          12.times do
            root = prog12.tick(:hc)
            # power chords (root + 5th)
            pch =
            case root
            when :c2 then (ring :c3, :g3)
            when :g1 then (ring :g2, :d3)
            when :a1 then (ring :a2, :e3)
            when :f1 then (ring :f2, :c3)
            end
            4.times do |i|
              sleep 0.5; play pch, amp: get(:e2); play (pch + 12), amp: get(:e2); sleep 0.5
end end end end end end end

# e3
live_loop :lead_blade do
  use_synth :blade
  with_fx :distortion, distort: 0.35 do
    with_fx :reverb, room: 0.7, mix: 0.45 do
      amp_val = get(:e3) || 0   # fallback safety
      [
        :e4,0.25,:g4,0.25,:a4,0.5,:g4,0.25,:e4,0.25,
        :g4,0.25,:a4,0.25,[:c5,0.4],0.75,
        :b4,0.25,:a4,0.25,:g4,0.5,:a4,0.25,
        :b4,0.25,:d5,0.5,[:g5,0],0.5,
        :c5,0.25,:e5,0.25,:g5,0.5,:e5,0.25,
        :d5,0.25,:c5,0.5,[:a4,0.35],0.75,
        :a4,0.25,:c5,0.25,:e5,0.25,:f5,0.25,
        :e5,0.25,:c5,0.25,:a4,0.5,[:c5,0.6],1
      ].each_slice(2) do |n, d|
        
        amp_val = get(:e3)
        if n.is_a?(Array)
          play n[0],
            amp: amp_val, sustain: n[1], cutoff: 95, vibrato_rate: 6, vibrato_depth: 0.15
        else
          play n,
            amp: amp_val, sustain: 0.12, release: 0.28, cutoff: 95, vibrato_rate: 6, vibrato_depth: 0.15
        end
        sleep d
end end end end
# e4
live_loop :bass_hold do
  use_synth :dark_ambience
  play :c4, sustain: 16, release: 4, amp: get(:e4)*3
  sleep 16
end