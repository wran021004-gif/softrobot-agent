function info = encode_saved_frames(folder, output, fps)
% Encode native renderer PNG frames. No scene drawing or numerical simulation.
files=dir(fullfile(folder,'frame_*.png'));
assert(~isempty(files),'No native frames to encode.');
writer=VideoWriter(output,'MPEG-4'); writer.FrameRate=fps; writer.Quality=90;
open(writer); cleanup=onCleanup(@()close(writer));
for k=1:numel(files)
    writeVideo(writer,imread(fullfile(folder,files(k).name)));
end
clear cleanup;
reader=VideoReader(output); count=0;
while hasFrame(reader), readFrame(reader); count=count+1; end
assert(count==numel(files),'Encoded video frame count mismatch.');
info=struct('encoder','MATLAB VideoWriter MPEG-4','decoded_frame_count',count, ...
    'duration_s',reader.Duration,'width',reader.Width,'height',reader.Height);
end
