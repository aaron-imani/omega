#! /bin/zsh
# Saving understand path in a variable
und_path="/Applications/Understand.app/Contents/MacOS/und"

# Iterate over all projects and create an understand db for each in the program_contexts folder
for project in $(ls -d Projects/*); do
    project=${project%/}
    # Project name is the last part of the path
    project_name=$(basename $project)
    echo "Creating understand db for $project_name"
    $und_path create -languages Java program_contexts/understand_projects/$project_name.und
    $und_path add $project program_contexts/understand_projects/$project_name.und
done