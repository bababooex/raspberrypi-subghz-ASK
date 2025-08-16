#!/bin/bash
#Script uses whiptail to create "user friendly" interface

# === File and GPIO configuration ===
RFRP_SCRIPT="rfrp.py"
RFRP_FILE="saved_codes.json"
BRUTE_SCRIPT="sub_bruteforce.py"
SUBRUTE_DIR="./sub_brute_files"
JAM_SCRIPT="jammer.py"
JAM_FILE="jammer.sub"
SUBSEND_SCRIPT="sub_converter.py"
SUBCUSTOM_DIR="./sub_custom_files"
TX_GPIO=13
RX_GPIO=25
# ===================================

whiptail --msgbox "Hello!\nActivating pigpiod!" 10 50
sudo pigpiod

while true; do
  CHOICE=$(whiptail --title "433MHz Control Menu" --menu "Select an option:" 20 60 10 \
    "1" "Record 433MHz code (rfrp)" \
    "2" "Send 433MHz code (rfrp)"\
    "3" "Delete 433MHz code (rfrp)" \
    "4" ".sub file bruteforce" \
    "5" "Custom .sub file" \
    "6" "Jam 433MHz band" \
    "7" "Exit" 3>&1 1>&2 2>&3)

  case "$CHOICE" in
    "1")
      CODE_NAME=$(whiptail --inputbox "Enter a name for the 433 MHz code (underscores only):" 10 60 3>&1 1>&2 2>&3)
      if [[ ! "$CODE_NAME" =~ ^[a-zA-Z0-9_]+$ ]]; then
        whiptail --msgbox "Bad character used!\nUse only letters, numbers, underscores." 10 50
        continue
      fi
      RECORD_TIME=$(whiptail --inputbox "Recording time in ms (default 500):" 10 50 "500" 3>&1 1>&2 2>&3)
      python3 "$RFRP_SCRIPT" --record --name "$CODE_NAME" --time "$RECORD_TIME" --file "$RFRP_FILE" --rx "$RX_GPIO" || whiptail --msgbox "Error running Python script." 10 50
      ;;
    "2")
      if [ ! -s "$RFRP_FILE" ] || [ "$(jq -r 'keys | length' "$RFRP_FILE")" -eq 0 ]; then
        whiptail --msgbox "No 433 MHz codes found in $RFRP_FILE" 10 50
        continue
      fi
      MENU_ITEMS=""
      while IFS= read -r name; do
        MENU_ITEMS+=" $name $name"
      done < <(jq -r 'keys[]' "$RFRP_FILE")

      CODE_TO_PLAY=$(whiptail --title "Send 433MHz Code" --menu "Choose a code to send:" 20 60 10 $MENU_ITEMS 3>&1 1>&2 2>&3)
      if [ -n "$CODE_TO_PLAY" ]; then
        python3 "$RFRP_SCRIPT" --send --name "$CODE_TO_PLAY" --file "$RFRP_FILE" --tx "$TX_GPIO" || whiptail --msgbox "Error running Python script." 10 50
      else
        whiptail --msgbox "Going back to menu!" 10 50
      fi
      ;;
    "3")
      if [ ! -s "$RFRP_FILE" ] || [ "$(jq -r 'keys | length' "$RFRP_FILE")" -eq 0 ]; then
        whiptail --msgbox "No 433 MHz codes found in $RFRP_FILE" 10 50
        continue
      fi
      MENU_ITEMS=""
      while IFS= read -r name; do
        MENU_ITEMS+=" $name $name"
      done < <(jq -r 'keys[]' "$RFRP_FILE")

      CODE_TO_DELETE=$(whiptail --title "Delete 433MHz Code" --menu "Select a code to delete:" 20 60 10 $MENU_ITEMS 3>&1 1>&2 2>&3)
      if [ -n "$CODE_TO_DELETE" ]; then
        whiptail --yesno "Are you sure you want to delete '$CODE_TO_DELETE'?" 10 50
        if [ $? -eq 0 ]; then
          jq "del(.\"$CODE_TO_DELETE\")" "$RFRP_FILE" > /tmp/ask_tmp.json && mv /tmp/ask_tmp.json "$RFRP_FILE"
          whiptail --msgbox "Code '$CODE_TO_DELETE' deleted." 10 50
        fi
      else
        whiptail --msgbox "Going back to menu!" 10 50
      fi
      ;;
    "4")
      if [ ! -d "$SUBRUTE_DIR" ]; then
        whiptail --msgbox "Directory $SUBRUTE_DIR not found!" 10 50
        continue
      fi

      SUB_MENU_ITEMS=""
      for file in "$SUBRUTE_DIR"/*.sub; do
        [ -e "$file" ] || continue
        filename=$(basename "$file")
        SUB_MENU_ITEMS+=" $filename $filename"
      done

      SELECTED_SUB=$(whiptail --title "Select .sub File" --menu "Choose a .sub file to send:" 20 60 10 $SUB_MENU_ITEMS 3>&1 1>&2 2>&3)
      if [ -z "$SELECTED_SUB" ]; then
        whiptail --msgbox "No file selected. Returning to menu." 10 50
        continue
      fi

      REPEAT=$(whiptail --inputbox "Number of repeat per RAW_Data line?" 10 60 "3" 3>&1 1>&2 2>&3)
      DELAY=$(whiptail --inputbox "Delay between RAW lines in ms?" 10 60 "300" 3>&1 1>&2 2>&3)
      whiptail --msgbox "Starting bruteforce with $SELECTED_SUB with user set $REPEAT X repeat and $DELAY ms delay" 10 60
      python3 "$BRUTE_SCRIPT" "$SUBRUTE_DIR/$SELECTED_SUB" "$REPEAT" "$DELAY" "$TX_GPIO" || whiptail --msgbox "Error running Python script, only RAW .sub files are supported!" 10 50
      whiptail --msgbox "Going back to menu!" 10 50
      ;;
    "5")
      if [ ! -d "$SUBCUSTOM_DIR" ]; then
        whiptail --msgbox "Directory $SUBCUSTOM_DIR not found!" 10 50
        continue
      fi

      SUB_MENU_ITEMS=""
      for file in "$SUBCUSTOM_DIR"/*.sub; do
        [ -e "$file" ] || continue
        filename=$(basename "$file")
        SUB_MENU_ITEMS+=" $filename $filename"
      done

      SELECTED_SUB=$(whiptail --title "Select .sub File" --menu "Choose a .sub file to send:" 20 60 10 $SUB_MENU_ITEMS 3>&1 1>&2 2>&3)
      if [ -z "$SELECTED_SUB" ]; then
        whiptail --msgbox "No file selected. Returning to menu." 10 50
        continue
      fi
      CHAIN_LENGHT=$(whiptail --inputbox "Lengh of a chain (prevent crashing)?" 10 60 "1000" 3>&1 1>&2 2>&3)
      whiptail --msgbox "Sending custom file with name $SELECTED_SUB using wave_chaining" 10 60
      python3 "$SUBSEND_SCRIPT" "$SUBCUSTOM_DIR/$SELECTED_SUB" "$CHAIN_LENGHT" "$TX_GPIO" || whiptail --msgbox "Error running Python script. Possibly no more CBS or unsupported protocol!" 10 50
      whiptail --msgbox "Going back to menu!" 10 50
      ;;
    "6")
      whiptail --msgbox "Jamming started... Press Ctrl+C to return." 10 50
      python3 "$JAM_SCRIPT" "$JAM_FILE" "$TX_GPIO"
      whiptail --msgbox "Going back to menu!" 10 50
      ;;
    "7")
      whiptail --msgbox "Deactivating pigpiod!\nGood bye!" 10 50
      sudo pigpiod kill
      break
      ;;
      *)
      whiptail --msgbox "Deactivating pigpiod!\nGood bye!" 10 50
      sudo pigpiod kill
      break
      ;;
  esac
done
