#!/usr/bin/env bash

set -u

QUESTIONS=(
  "Is it alive?"
  "Can it usually fit in a backpack?"
  "Is it usually used indoors?"
  "Does it commonly run on electricity?"
  "Is it man-made?"
  "Can it move on its own?"
  "Would you commonly find it in a home?"
  "Is it larger than a microwave?"
  "Could you buy it at a grocery store?"
  "Is it mainly used for entertainment?"
)

THINGS=(
  "cat"
  "oak tree"
  "car"
  "bicycle"
  "laptop"
  "book"
  "refrigerator"
  "banana"
  "soccer ball"
  "television"
  "airplane"
  "toaster"
  "goldfish"
  "mountain"
  "piano"
  "smartphone"
)

FEATURES=(
  "1010111000" # cat
  "1010010010" # oak tree
  "0011110010" # car
  "0010110011" # bicycle
  "1111101101" # laptop
  "1100101101" # book
  "0011101110" # refrigerator
  "1100011110" # banana
  "1000111011" # soccer ball
  "1111101111" # television
  "0011110011" # airplane
  "1111101110" # toaster
  "1010011100" # goldfish
  "0010010010" # mountain
  "1110101111" # piano
  "1111101101" # smartphone
)

read_yes_no() {
  local prompt=$1
  local reply
  while true; do
    read -r -p "$prompt [y/n]: " reply
    reply=${reply,,}
    case "$reply" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) echo "Please answer with y or n." ;;
    esac
  done
}

best_question_for_candidates() {
  local -n _candidates=$1
  local -n _asked=$2
  local n=${#_candidates[@]}
  local best_index=-1
  local best_score=$((n + 1))
  local i idx yes_count diff score

  for ((i = 0; i < ${#QUESTIONS[@]}; i++)); do
    [[ ${_asked[$i]} -eq 1 ]] && continue
    yes_count=0
    for idx in "${_candidates[@]}"; do
      [[ ${FEATURES[$idx]:$i:1} == "1" ]] && ((yes_count++))
    done
    diff=$((n - (2 * yes_count)))
    ((diff < 0)) && diff=$((-diff))
    score=$diff
    if ((score < best_score)); then
      best_score=$score
      best_index=$i
    fi
  done

  echo "$best_index"
}

play_game() {
  local max_questions=20
  local questions_used=0
  local q_index idx
  local candidates=()
  local next_candidates=()
  local asked=()
  local guessed=()

  for ((idx = 0; idx < ${#THINGS[@]}; idx++)); do
    candidates+=("$idx")
    guessed+=("0")
  done
  for ((idx = 0; idx < ${#QUESTIONS[@]}; idx++)); do
    asked+=("0")
  done

  echo
  echo "Think of one thing from everyday life."
  echo "I'll ask yes/no questions and try to guess it within $max_questions questions."

  while ((questions_used < max_questions && ${#candidates[@]} > 1)); do
    q_index=$(best_question_for_candidates candidates asked)
    ((q_index < 0)) && break
    asked[$q_index]=1
    ((questions_used++))

    if read_yes_no "Q$questions_used: ${QUESTIONS[$q_index]}"; then
      next_candidates=()
      for idx in "${candidates[@]}"; do
        [[ ${FEATURES[$idx]:$q_index:1} == "1" ]] && next_candidates+=("$idx")
      done
    else
      next_candidates=()
      for idx in "${candidates[@]}"; do
        [[ ${FEATURES[$idx]:$q_index:1} == "0" ]] && next_candidates+=("$idx")
      done
    fi

    if ((${#next_candidates[@]} == 0)); then
      echo "Those answers don't match my knowledge base, so I'll start guessing anyway."
      break
    fi
    candidates=("${next_candidates[@]}")
  done

  for idx in "${candidates[@]}"; do
    ((questions_used >= max_questions)) && break
    [[ ${guessed[$idx]} -eq 1 ]] && continue
    guessed[$idx]=1
    ((questions_used++))
    if read_yes_no "Q$questions_used: Is it ${THINGS[$idx]}?"; then
      echo "Nice! I guessed it in $questions_used questions."
      return 0
    fi
  done

  for ((idx = 0; idx < ${#THINGS[@]} && questions_used < max_questions; idx++)); do
    [[ ${guessed[$idx]} -eq 1 ]] && continue
    guessed[$idx]=1
    ((questions_used++))
    if read_yes_no "Q$questions_used: Is it ${THINGS[$idx]}?"; then
      echo "Got it! I needed $questions_used questions."
      return 0
    fi
  done

  echo "I couldn't guess it within $max_questions questions."
  return 1
}

echo "=== Bash 20 Questions ==="
while true; do
  play_game
  echo
  if ! read_yes_no "Play again?"; then
    echo "Thanks for playing."
    break
  fi
done
