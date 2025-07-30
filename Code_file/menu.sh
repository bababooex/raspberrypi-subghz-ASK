#!/bin/bash
# Script uses whiptail to create "user friendly" interface, similar to TV-B-Gone menu.

# === File and GPIO configuration ===
RFRP_SCRIPT="rfrp.py"
RFRP_FILE="saved_codes.json"
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
    "4" "Exit" 3>&1 1>&2 2>&3)

  case "$CHOICE" in
    "1")
      CODE_NAME=$(whiptail --inputbox "Enter a name for the 433 MHz code (underscores only):" 10 60 3>&1 1>&2 2>&3)
      if [[ ! "$CODE_NAME" =~ ^[a-zA-Z0-9_]+$ ]]; then
        whiptail --msgbox "Bad character used!\nUse only letters, numbers, underscores." 10 50
        continue
      fi
      RECORD_TIME=$(whiptail --inputbox "Recording time in ms (default 500):" 10 50 "500" 3>&1 1>&2 2>&3)
      python3 "$RFRP_SCRIPT" --record --name "$CODE_NAME" --time "$RECORD_TIME" --file "$RFRP_FILE" --rx "$RX_GPIO"
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
        python3 "$RFRP_SCRIPT" --send --name "$CODE_TO_PLAY" --file "$RFRP_FILE" --tx "$TX_GPIO"
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
