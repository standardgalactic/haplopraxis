#!/bin/bash

# List of new names
new_names=(
    "Maldeittotor"
        "Dyde"
	    "Thellatnlur"
	        "Ttermcusowy"
		    "Cupekorug"
		        "Mierr"
			    "Lorndegl"
			        "Jalerg"
				    "Thouerch"
				        "Scck"
					    "Atzmeriz"
					        "Prrstey"
						    "Esometleusel"
						        "Cdeloro"
							    "Warin"
							        "Gttt"
								    "Ppplisilondo"
								        "Mbusr"
									    "Nnnsek"
									        "Wasinrrmeka"
									)

									# Get all .webp files in the current directory
									webp_files=(*.webp)

									# Loop through the webp files and rename them
									for i in "${!webp_files[@]}"; do
										    if [[ $i -lt ${#new_names[@]} ]]; then
											            mv "${webp_files[$i]}" "${new_names[$i]}.webp"
												            echo "Renamed '${webp_files[$i]}' to '${new_names[$i]}.webp'"
													        else
															        echo "Not enough names for all files. Remaining files will not be renamed."
																        break
																	    fi
																    done

