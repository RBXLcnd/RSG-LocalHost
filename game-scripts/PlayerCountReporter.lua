-- Script for ServerScriptService. Sends the player count to the RSG LocalHost app
-- (which shows it in the Discord /server-status panel).
-- Requires: Game Settings > Security > "Allow HTTP Requests" turned on.

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")

local URL = "http://127.0.0.1:55557/players"
local INTERVAL = 30 -- seconds (the app treats the count as "unknown" after 150 s without a signal)

local function report(exclude)
	local count = 0
	for _, p in ipairs(Players:GetPlayers()) do
		if p ~= exclude then count += 1 end
	end
	local ok, err = pcall(function()
		HttpService:PostAsync(URL, HttpService:JSONEncode({ count = count }), Enum.HttpContentType.ApplicationJson)
	end)
	if not ok then
		warn("[PlayerCount] could not reach the RSG LocalHost app:", err)
	end
end

Players.PlayerAdded:Connect(function() task.defer(report) end)
Players.PlayerRemoving:Connect(function(plr) task.defer(report, plr) end)

report()
while true do
	task.wait(INTERVAL)
	report()
end
